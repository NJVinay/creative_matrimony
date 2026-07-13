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


# ── Epic I1: expert consultation sessions (tier-gated booking) ──────

class SessionStatus(str, enum.Enum):
    requested = "requested"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class ExpertSession(Base):
    __tablename__ = "expert_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expert_user_id = Column(Integer, ForeignKey("users.id"), nullable=True,
                            doc="Assigned expert (set on confirmation)")

    category = Column(Enum(ExpertCategory), nullable=False, default=ExpertCategory.matchmaking)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False, default=30)
    status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.requested)

    notes = Column(Text, nullable=True)
    reminder_sent = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ── Epic I2: Personal Care mode ─────────────────────────────────────

class CareStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    closed = "closed"


class CareAssignment(Base):
    """Dedicated-expert engagement for a member (Personal Care mode)."""
    __tablename__ = "care_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expert_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(CareStatus), nullable=False, default=CareStatus.active)
    # Fee is recorded here; collection goes through the payment provider
    # once a real gateway (Razorpay) is integrated.
    service_fee = Column(Integer, nullable=False, default=0, doc="Fee in INR")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class CareTask(Base):
    """Checklist item inside a Personal Care engagement."""
    __tablename__ = "care_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("care_assignments.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    is_done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)


class CareCallLog(Base):
    """Log of expert calls made within a Personal Care engagement."""
    __tablename__ = "care_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("care_assignments.id"), nullable=False, index=True)
    called_at = Column(DateTime, server_default=func.now(), nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
