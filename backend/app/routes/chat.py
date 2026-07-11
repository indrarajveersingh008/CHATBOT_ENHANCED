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
from ..utils.helpers import is_image_file, guess_image_mime_type
from ..ai.client import ask_ai, generate_conversation_title

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

        requested_model = request.model_name or settings.MODEL_NAME

        # No conversation yet (first message, or bad id) -> start a new one.
        if conversation is None:
            title = generate_conversation_title(request.message, requested_model)
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
            if is_image_file(f_record.filename, f_record.content_type):
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
            image_files = [f for f in db_files if is_image_file(f.filename, f.content_type)]
            for img_file in image_files:
                file_path = os.path.join(settings.UPLOAD_DIR, img_file.stored_name)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                            attached_images.append({
                                "content_type": guess_image_mime_type(img_file.filename, img_file.content_type),
                                "base64_data": encoded_string
                            })
                    except Exception as e:
                        print(f"Error encoding image {img_file.filename}: {e}")

        if attached_images and requested_model not in settings.VISION_CAPABLE_MODELS:
            print(f"Auto-switching to vision model for image analysis (was: {requested_model})")
            requested_model = settings.DEFAULT_VISION_MODEL

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

