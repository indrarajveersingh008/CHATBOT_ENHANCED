import os
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database.db import get_db
from ..models.models import Conversation, Message, UploadedFile, User
from ..config.settings import settings
from ..utils.file_reader import read_file_content
from ..utils.helpers import is_image_file, guess_image_mime_type
from ..utils.youtube import get_youtube_context
from ..ai.client import ask_ai, generate_conversation_title
from ..utils.security import get_current_user

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    model_name: Optional[str] = None
    file_ids: Optional[list[int]] = None


@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        conversation = None
        if request.conversation_id is not None:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == request.conversation_id, Conversation.user_id == current_user.id)
                .first()
            )
            if not conversation:
                raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

        requested_model = request.model_name or settings.MODEL_NAME

        # No conversation yet (first message, or bad id) -> start a new one.
        if conversation is None:
            title = generate_conversation_title(request.message, requested_model)
            conversation = Conversation(title=title, user_id=current_user.id)
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
                (UploadedFile.user_id == current_user.id) &
                ((UploadedFile.conversation_id == None) |
                 (UploadedFile.conversation_id == conversation.id))
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

        # Check for YouTube link and fetch transcript context
        youtube_context = get_youtube_context(request.message)
        if youtube_context:
            if files_context:
                files_context = f"{files_context}\n\n{youtube_context}"
            else:
                files_context = youtube_context

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

        bot_msg = Message(conversation_id=conversation.id, sender="bot", content=reply)
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)

        return {
            "reply": reply,
            "conversation_id": conversation.id,
            "user_message_id": user_msg.id,
            "bot_message_id": bot_msg.id,
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "reply": "⚠️ Sorry, I couldn't process your request.",
            "error": str(e),
        }


class EditRequest(BaseModel):
    message_id: int
    message: str
    model_name: Optional[str] = None


@router.post("/chat/edit")
def edit_or_retry(request: EditRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # 1. Find the target user message
        target_message = db.query(Message).filter(Message.id == request.message_id).first()
        if not target_message:
            raise HTTPException(status_code=404, detail="Message not found")

        conversation = target_message.conversation
        if conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

        requested_model = request.model_name or settings.MODEL_NAME

        # 2. Delete all subsequent messages in the conversation (where message.id > target_message.id)
        db.query(Message).filter(
            Message.conversation_id == conversation.id,
            Message.id > target_message.id
        ).delete(synchronize_session=False)

        # 3. Update the target user message content
        target_message.content = request.message
        db.commit()

        # 4. Refresh conversation to sync relationship cache
        db.refresh(conversation)

        # Build history from messages BEFORE the target message
        history = []
        for m in conversation.messages:
            if m.id < target_message.id:
                history.append({"sender": m.sender, "content": m.content})

        # 5. Gather context from files for the conversation
        uploaded_files = (
            db.query(UploadedFile)
            .filter(
                (UploadedFile.user_id == current_user.id) &
                ((UploadedFile.conversation_id == None) |
                 (UploadedFile.conversation_id == conversation.id))
            )
            .all()
        )
        files_context_parts = []
        total_length = 0
        MAX_TOTAL_CHARS = 200000

        for f_record in uploaded_files:
            # Skip image files for standard text context
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

        # Check for YouTube link and fetch transcript context
        youtube_context = get_youtube_context(request.message)
        if youtube_context:
            if files_context:
                files_context = f"{files_context}\n\n{youtube_context}"
            else:
                files_context = youtube_context

        # 6. Gather images attached to the target user message
        db_files = target_message.files
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
            requested_model = settings.DEFAULT_VISION_MODEL

        # 7. Query AI
        reply = ask_ai(request.message, history, files_context, requested_model, attached_images=attached_images)

        # 8. Save bot response
        bot_msg = Message(conversation_id=conversation.id, sender="bot", content=reply)
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)

        return {
            "reply": reply,
            "conversation_id": conversation.id,
            "user_message_id": target_message.id,
            "bot_message_id": bot_msg.id
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


