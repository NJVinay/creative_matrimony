"""
Expert Services Model.
Trace: @context_documents/MVP_BACKLOG.md Epic I
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Enum, func
from app.database import Base

class ExpertCategory(str, enum.Enum):
    matchmaking = "matchmaking"
    astrology = "astrology"
    profile_writing = "profile_writing"
    other = "other"

class ExpertInquiry(Base):
    __tablename__ = "expert_inquiries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    category = Column(Enum(ExpertCategory), nullable=False)
    message = Column(Text, nullable=False)
    
    # Contact info might be different from profile? For MVP assume User phone/email.
    preferred_contact_time = Column(String(100), nullable=True)
    
    is_resolved = Column(Boolean, default=False)
    admin_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
