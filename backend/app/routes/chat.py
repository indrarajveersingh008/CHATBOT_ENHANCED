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
    file_ids: Optional[list[int]] = None


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

        user_msg = Message(conversation_id=conversation.id, sender="user", content=request.message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        db_files = []
        if request.file_ids:
            db_files = db.query(UploadedFile).filter(UploadedFile.id.in_(request.file_ids)).all()
            for f in db_files:
                f.conversation_id = conversation.id
                f.message_id = user_msg.id
            db.commit()

        # Load context from uploaded files (global + local to this conversation)
        uploaded_files = (
            db.query(UploadedFile)
            .filter(
                (UploadedFile.conversation_id == None) |
                (UploadedFile.conversation_id == conversation.id)
            )
            .all()
        )
        files_context_parts = []
        total_length = 0
        MAX_TOTAL_CHARS = 200000  # Context length ceiling to prevent overflow

        for f_record in uploaded_files:
            # Skip image files from text context extraction since they are handled natively by multimodal models
            if f_record.content_type and f_record.content_type.startswith("image/"):
                continue

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

        # Base64 encode attached images for the vision model
        attached_images = []
        if db_files:
            import base64
            image_files = [f for f in db_files if f.content_type and f.content_type.startswith("image/")]
            for img_file in image_files:
                file_path = os.path.join(settings.UPLOAD_DIR, img_file.stored_name)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                            attached_images.append({
                                "content_type": img_file.content_type,
                                "base64_data": encoded_string
                            })
                    except Exception as e:
                        print(f"Error encoding image {img_file.filename}: {e}")

        requested_model = request.model_name or settings.MODEL_NAME
        reply = ask_ai(request.message, history, files_context, requested_model, attached_images=attached_images)

        db.add(Message(conversation_id=conversation.id, sender="bot", content=reply))
        db.commit()

        return {"reply": reply, "conversation_id": conversation.id}

    except Exception as e:
        traceback.print_exc()
        return {
            "reply": "⚠️ Sorry, I couldn't process your request.",
            "error": str(e),
        }

