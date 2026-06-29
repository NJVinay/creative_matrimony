"""
Audit log for sensitive actions — immutable append-only.
Trace: @context_documents/SECURITY_PLANNER.md §2
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func, JSON
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, doc="e.g. otp_request, profile_update, ban_user")
    resource_type = Column(String(50), nullable=True, doc="e.g. user, profile, taxonomy")
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
