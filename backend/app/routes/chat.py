import os
import traceback
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database.db import get_db
from ..models.models import Conversation, Message, UploadedFile
from ..config.settings import settings
from ..utils.file_reader import read_file_content
from ..ai.client import ask_ai

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    model_name: Optional[str] = None


@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        conversation = None
        if request.conversation_id is not None:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == request.conversation_id)
                .first()
            )

        # No conversation yet (first message, or bad id) -> start a new one.
        if conversation is None:
            title = request.message.strip()[:40] or "New Chat"
            if len(request.message.strip()) > 40:
                title += "..."
            conversation = Conversation(title=title)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        history = [
            {"sender": m.sender, "content": m.content} for m in conversation.messages
        ]

        db.add(Message(conversation_id=conversation.id, sender="user", content=request.message))
        db.commit()

        # Load context from all uploaded files
        uploaded_files = db.query(UploadedFile).all()
        files_context_parts = []
        total_length = 0
        MAX_TOTAL_CHARS = 200000  # Context length ceiling to prevent overflow

        for f_record in uploaded_files:
            file_path = os.path.join(settings.UPLOAD_DIR, f_record.stored_name)
            content = read_file_content(file_path, f_record.filename)
            part = f"File: {f_record.filename}\nContent:\n{content}\n"
            
            if total_length + len(part) > MAX_TOTAL_CHARS:
                remaining = MAX_TOTAL_CHARS - total_length
                if remaining > 100:
                    files_context_parts.append(part[:remaining] + "\n[Context limit reached, remaining file content omitted...]")
                break
                
            files_context_parts.append(part)
            total_length += len(part)

        files_context = "\n\n".join(files_context_parts) if files_context_parts else None

        requested_model = request.model_name or settings.MODEL_NAME
        reply = ask_ai(request.message, history, files_context, requested_model)

        db.add(Message(conversation_id=conversation.id, sender="bot", content=reply))
        db.commit()

        return {"reply": reply, "conversation_id": conversation.id}

    except Exception as e:
        traceback.print_exc()
        return {
            "reply": "⚠️ Sorry, I couldn't process your request.",
            "error": str(e),
        }
