"""
User and OTP models.
Trace: @context_documents/BACKEND_PLANNER.md §1–§2, @context_documents/SECURITY_PLANNER.md §2
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Text, func
)
from app.database import Base


class UserRole(str, enum.Enum):
    member = "member"
    plus = "plus"
    premium = "premium"
    admin = "admin"
    moderator = "moderator"
    verification_officer = "verification_officer"
    expert = "expert"
    horoscope_expert = "horoscope_expert"
    personal_care_expert = "personal_care_expert"
    support = "support"
    finance = "finance"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.member, nullable=False)
    is_verified = Column(Boolean, default=False, doc="Identity-verified badge")
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class OTPLog(Base):
    __tablename__ = "otp_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    attempts = Column(Integer, default=0)
    cooldown_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    verified_at = Column(DateTime, nullable=True)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(255), unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)

