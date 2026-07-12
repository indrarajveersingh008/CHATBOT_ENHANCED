import os
import datetime
import hashlib
import jwt
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database.db import get_db
from ..models.models import User

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-for-ai-nexus-auth-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA-256 and a random salt."""
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored_password: str) -> bool:
    """Verify stored password against given password."""
    try:
        salt, hashed = stored_password.split(":")
        test_hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
        return test_hashed == hashed
    except Exception:
        return False

def create_access_token(username: str, is_admin: bool = False) -> str:
    """Generate JWT access token containing username as subject and admin flag."""
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "is_admin": is_admin,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[str]:
    """Decode JWT token and return username. Returns None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency to retrieve the current authenticated User."""
    token = None
    if credentials:
        token = credentials.credentials
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    username = decode_access_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user
