import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..models.models import User, Conversation, UploadedFile
from ..utils.security import get_current_user
from ..config.settings import settings

router = APIRouter(prefix="/admin", tags=["admin"])

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that checks if the active user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Fetch system-wide usage statistics and registered users list."""
    total_users = db.query(User).count()
    total_convs = db.query(Conversation).count()
    total_files = db.query(UploadedFile).count()
    
    users = db.query(User).order_by(User.created_at.desc()).all()
    users_list = []
    
    for u in users:
        users_list.append({
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "conversations_count": db.query(Conversation).filter(Conversation.user_id == u.id).count(),
            "files_count": db.query(UploadedFile).filter(UploadedFile.user_id == u.id).count()
        })
        
    return {
        "total_users": total_users,
        "total_conversations": total_convs,
        "total_files": total_files,
        "users": users_list
    }

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Permanently delete a user account and all associated conversation logs and physical files."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete themselves")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete physical files associated with the user
    for f_record in user.files:
        file_path = os.path.join(settings.UPLOAD_DIR, f_record.stored_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting physical file {file_path} for user {user_id}: {e}")
                
    db.delete(user)
    db.commit()
    return {"status": "deleted"}
