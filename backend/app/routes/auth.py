from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..models.models import User
from ..utils.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(request: AuthRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    password = request.password
    
    if len(username) < 3 or len(username) > 30:
        raise HTTPException(status_code=400, detail="Username must be between 3 and 30 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
    # Check if user already exists
    existing = db.query(User).filter(User.username.ilike(username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username is already taken")
        
    hashed = hash_password(password)
    is_admin = username.lower() == "admin"
    user = User(username=username, hashed_password=hashed, is_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(user.username)
    return {"token": token, "username": user.username, "is_admin": user.is_admin}

@router.post("/login")
def login(request: AuthRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    password = request.password
    
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    token = create_access_token(user.username)
    return {"token": token, "username": user.username, "is_admin": user.is_admin}
