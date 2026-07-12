from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.db import get_db
from ..models.models import Conversation, Message, User
from ..utils.security import get_current_user

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "files": [
                    {
                        "id": f.id,
                        "filename": f.filename,
                        "content_type": f.content_type,
                        "size": f.size,
                    }
                    for f in m.files
                ],
            }
            for m in conversation.messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete physical files associated with the conversation from disk
    import os
    from ..config.settings import settings
    for f_record in conversation.files:
        file_path = os.path.join(settings.UPLOAD_DIR, f_record.stored_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting physical file {file_path} for conversation {conversation_id}: {e}")

    db.delete(conversation)
    db.commit()
    return {"status": "deleted"}


@router.get("/search")
def search_messages(q: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Search across every stored message's content. Used by the sidebar Search panel."""
    q = q.strip()
    if not q:
        return []

    like_query = f"%{q}%"
    results = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Conversation.user_id == current_user.id,
            Message.content.ilike(like_query)
        )
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "conversation_id": m.conversation_id,
            "sender": m.sender,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in results
    ]
