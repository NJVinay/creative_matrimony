"""
Communication Models — Interests & Chat.
Trace: @context_documents/MVP_BACKLOG.md Epic G
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, DateTime, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base

class InterestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"

class Interest(Base):
    """
    Interest sent from one profile to another.
    Precursor to chatting.
    """
    __tablename__ = "interests"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    
    status = Column(String, default=InterestStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sender = relationship("Profile", foreign_keys=[sender_id], backref="interests_sent")
    receiver = relationship("Profile", foreign_keys=[receiver_id], backref="interests_received")


class ChatRoom(Base):
    """
    Active chat session between two users.
    Created when Interest is accepted.
    """
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")
    participants = relationship("ChatParticipant", back_populates="room", cascade="all, delete-orphan")


class ChatParticipant(Base):
    """Link table for ChatRoom users."""
    __tablename__ = "chat_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Link to User, not Profile, for simpler auth handling
    
    room = relationship("ChatRoom", back_populates="participants")
    user = relationship("User")


class ChatMessage(Base):
    """Message within a ChatRoom."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")
