"""
Safety models — panic block + banned-phone blocklist (ban evasion).
Trace: @context_documents/MVP_BACKLOG.md Epic J2,
       @context_documents/SAFETY_TRUST_PLANNER.md
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, func
)
from app.database import Base


class UserBlock(Base):
    """A user-initiated block (panic block). Symmetric enforcement:
    neither side can see, message, or be recommended the other."""
    __tablename__ = "user_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_user_id", "blocked_user_id", name="uq_user_block_pair"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    blocker_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    blocked_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class BannedPhone(Base):
    """Phones of permanently banned users. Blocks re-registration (ban evasion).
    Attempts to re-enter with a listed phone are audit-flagged."""
    __tablename__ = "banned_phones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, doc="User that was banned")
    reason = Column(Text, nullable=True)
    banned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
