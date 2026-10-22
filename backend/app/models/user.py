"""
User and OTP models.
Trace: @context_documents/BACKEND_PLANNER.md §1–§2, @context_documents/SECURITY_PLANNER.md §2
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Text, func
)
from sqlalchemy.orm import relationship
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
    email_digest_opt_in = Column(Boolean, default=False, nullable=False,
                                 doc="Consent for weekly match digest emails (Epic G2)")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    profile = relationship("Profile", backref="user", uselist=False)


class OTPLog(Base):
    __tablename__ = "otp_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    attempts = Column(Integer, default=0)
    cooldown_until = Column(DateTime, nullable=True)  # legacy, no longer written or read
    # sha256 of the otp_device cookie of the browser that requested the code:
    # only that browser can check it. A verified row marks a device as known
    # to the phone (exempt from OTP_MAX_SENDS_PER_HOUR).
    device_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    verified_at = Column(DateTime, nullable=True)


class OTPPhoneLock(Base):
    """One row per phone, row-locked for the length of an OTP request so the
    per-phone throttles are checked and the new code written atomically."""
    __tablename__ = "otp_phone_locks"

    phone = Column(String(20), primary_key=True)
    locked_at = Column(DateTime, nullable=True)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(255), unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)

