import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from ..database.db import Base


class User(Base):
    """User account details for authentication and workspace segregation."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_admin = Column(Boolean, default=False)

    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    files = relationship(
        "UploadedFile",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Conversation(Base):
    """A single chat thread, shown in the sidebar 'Memory' panel."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Associated user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )
    files = relationship(
        "UploadedFile",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(Base):
    """One message (user or bot) inside a conversation."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender = Column(String(10))  # "user" or "bot"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    files = relationship(
        "UploadedFile",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class UploadedFile(Base):
    """Metadata for a file uploaded through the 'Files' panel."""

    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    stored_name = Column(String(255))
    content_type = Column(String(100), nullable=True)
    size = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    
    # Associated user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    user = relationship("User", back_populates="files")
    conversation = relationship("Conversation", back_populates="files")
    message = relationship("Message", back_populates="files")
