"""
User reports — abuse, harassment, fake profile, inappropriate content.
Trace: @context_documents/MVP_BACKLOG.md Epic J
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, ForeignKey, func,
)
from app.database import Base


class ReportReason(str, enum.Enum):
    fake_profile = "fake_profile"
    harassment = "harassment"
    inappropriate_photo = "inappropriate_photo"
    spam = "spam"
    age_misrepresentation = "age_misrepresentation"
    other = "other"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    investigating = "investigating"
    resolved = "resolved"
    dismissed = "dismissed"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(Enum(ReportReason), nullable=False)
    evidence_text = Column(Text, nullable=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.pending, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
