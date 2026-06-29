"""
OTP service — generation, hashing, verification, and sending.
Mock provider logs OTP to console for local dev.
Trace: @context_documents/BACKEND_PLANNER.md §1, @context_documents/SECURITY_PLANNER.md §2
"""

import hashlib
import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import OTPLog


def _generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _hash_otp(otp: str) -> str:
    """One-way hash for OTP storage (not stored in plain text)."""
    return hashlib.sha256(otp.encode()).hexdigest()


def _now_utc() -> datetime:
    """Timezone-aware UTC now (single source of truth)."""
    return datetime.now(timezone.utc)


def _aware_utc(dt: datetime | None) -> datetime | None:
    """
    SQLite returns naive datetimes; treat stored timestamps as UTC
    by stamping tzinfo on read. Centralized so we don't sprinkle
    `replace(tzinfo=...)` calls through the codebase.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get_active_otp(db: AsyncSession, phone: str) -> OTPLog | None:
    """Get the most recent unexpired, unverified OTP for a phone."""
    cutoff = _now_utc() - timedelta(seconds=settings.OTP_EXPIRE_SECONDS)
    result = await db.execute(
        select(OTPLog)
        .where(
            OTPLog.phone == phone,
            OTPLog.verified_at.is_(None),
            OTPLog.created_at >= cutoff,
        )
        .order_by(OTPLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def is_on_cooldown(db: AsyncSession, phone: str) -> bool:
    """Check if the phone is in OTP cooldown (too many failed attempts)."""
    otp_log = await get_active_otp(db, phone)
    if otp_log and otp_log.cooldown_until:
        cooldown_until = _aware_utc(otp_log.cooldown_until)
        return _now_utc() < cooldown_until
    return False


async def create_otp(db: AsyncSession, phone: str) -> str:
    """Generate and store a new OTP. Returns the raw OTP (for mock sending)."""
    otp = _generate_otp(settings.OTP_LENGTH)
    otp_log = OTPLog(
        phone=phone,
        otp_hash=_hash_otp(otp),
        attempts=0,
    )
    db.add(otp_log)
    await db.flush()
    return otp


async def verify_otp(db: AsyncSession, phone: str, otp: str) -> bool:
    """
    Verify an OTP. Returns True if valid, False otherwise.
    Increments attempt counter; sets cooldown after max attempts.
    """
    otp_log = await get_active_otp(db, phone)
    if not otp_log:
        return False

    # Check cooldown
    if otp_log.cooldown_until:
        cooldown_until = _aware_utc(otp_log.cooldown_until)
        if _now_utc() < cooldown_until:
            return False

    # Verify hash
    if _hash_otp(otp) == otp_log.otp_hash:
        otp_log.verified_at = _now_utc()
        await db.flush()
        return True

    # Wrong OTP — increment attempts
    otp_log.attempts += 1
    if otp_log.attempts >= settings.OTP_MAX_ATTEMPTS:
        otp_log.cooldown_until = _now_utc() + timedelta(
            seconds=settings.OTP_COOLDOWN_SECONDS
        )
    await db.flush()
    return False


async def send_otp(phone: str, otp: str) -> None:
    """Send OTP via configured provider. Mock provider just logs to console."""
    if settings.OTP_PROVIDER == "mock":
        print(f"\n{'='*50}")
        print(f"  [MOCK OTP] Phone: {phone}  |  OTP: {otp}")
        print(f"{'='*50}\n")
    else:
        # Future: Twilio / MSG91 / 2Factor integration
        raise NotImplementedError(f"OTP provider '{settings.OTP_PROVIDER}' not implemented yet")
