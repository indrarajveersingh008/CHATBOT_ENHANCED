from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.db import get_db
from ..models.models import Conversation, Message

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db)):
    conversations = (
        db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    )
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in conversation.messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
    return {"status": "deleted"}


@router.get("/search")
def search_messages(q: str = "", db: Session = Depends(get_db)):
    """Search across every stored message's content. Used by the sidebar Search panel."""
    q = q.strip()
    if not q:
        return []

    like_query = f"%{q}%"
    results = (
        db.query(Message)
        .filter(Message.content.ilike(like_query))
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
