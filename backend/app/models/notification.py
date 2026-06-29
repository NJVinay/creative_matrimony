"""
Notification model — System, Match, and Payment alerts.
Trace: @context_documents/MVP_BACKLOG.md Epic K
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, JSON, func
)
from app.database import Base


class NotificationType(str, enum.Enum):
    system = "system"
    match = "match"
    interest = "interest"
    payment = "payment"
    compliance = "compliance"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(100), nullable=False)
    body = Column(String(500), nullable=False)
    data = Column(JSON, nullable=True)  # Deep link data e.g., { profile_id: 123 }
    
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
