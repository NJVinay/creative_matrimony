"""
OTP service — generation, hashing, verification, and sending.
Providers: mock (console log), fast2sms (India SMS), whatsapp (Cloud API).
Trace: @context_documents/BACKEND_PLANNER.md §1, @context_documents/SECURITY_PLANNER.md §2
"""

import hashlib
import random
import re
import string
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import OTPLog


class OTPDeliveryError(RuntimeError):
    """Raised when the configured provider could not deliver the OTP.
    The API layer turns this into a clean 502 so the client can retry
    (the DB transaction rolls back, so no cooldown is burned)."""


def _generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _hash_otp(otp: str) -> str:
    """One-way hash for OTP storage (not stored in plain text)."""
    return hashlib.sha256(otp.encode()).hexdigest()


def _now_utc() -> datetime:
    """Naive UTC now (single source of truth).

    All DateTime columns are timestamp-without-timezone, and asyncpg
    (PostgreSQL/Neon) rejects tz-aware values for them outright — so the
    whole service works in naive UTC. SQLite tolerated aware values, which
    is why this only surfaced in production.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive_utc(dt: datetime | None) -> datetime | None:
    """Normalize a stored timestamp to naive UTC for comparisons
    (guards against legacy rows written with tzinfo attached)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
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
    """
    Check if the phone is in OTP cooldown.

    Returns True if EITHER:
      (a) Any unexpired OTPLog was created within the last
          OTP_COOLDOWN_SECONDS seconds (per-phone rate limit, enforced as an
          application-level cooldown so a first-time request cannot bypass
          OTP_RATE_LIMIT_PER_PHONE).
      (b) The most recent OTPLog has cooldown_until set (post-failed-attempts
          lockout, which OTP_MAX_ATTEMPTS triggers).

    Used by /auth/otp/request to throttle OTP requests before creating or
    sending any new OTP. SlowAPI's IP-based limit (OTP_RATE_LIMIT_PER_IP) is
    orthogonal: an attacker rotating phones cannot avoid (a) because it keys
    on the phone from the request body.
    """
    # (a) Per-phone cooldown window — every freshly-issued OTP starts a cooldown.
    recent_cutoff = _now_utc() - timedelta(seconds=settings.OTP_COOLDOWN_SECONDS)
    recent_result = await db.execute(
        select(OTPLog)
        .where(
            OTPLog.phone == phone,
            OTPLog.created_at >= recent_cutoff,
        )
        .order_by(OTPLog.created_at.desc())
        .limit(1)
    )
    if recent_result.scalar_one_or_none() is not None:
        return True

    # (b) Existing failed-attempts cooldown.
    otp_log = await get_active_otp(db, phone)
    if otp_log and otp_log.cooldown_until:
        cooldown_until = _naive_utc(otp_log.cooldown_until)
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
        cooldown_until = _naive_utc(otp_log.cooldown_until)
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


# ── Delivery providers ──────────────────────────────────────

def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def _whatsapp_number(phone: str) -> str:
    """WhatsApp wants E.164 digits without '+'. A bare 10-digit number is
    assumed Indian (the product is India-first)."""
    d = _digits(phone)
    return f"91{d}" if len(d) == 10 else d


def _fast2sms_number(phone: str) -> str:
    """Fast2SMS wants the 10-digit Indian subscriber number (no country code)."""
    d = _digits(phone)
    if len(d) > 10 and d.startswith("91"):
        d = d[-10:]
    return d


async def _send_via_fast2sms(phone: str, otp: str) -> None:
    """Fast2SMS OTP route — uses their pre-approved shared-DLT template
    ('{#var#} is your verification code'), so no business DLT is needed.
    Docs: https://docs.fast2sms.com/  (route=otp)"""
    number = _fast2sms_number(phone)
    if len(number) != 10:
        raise OTPDeliveryError("SMS delivery is currently available for Indian numbers only.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://www.fast2sms.com/dev/bulkV2",
                headers={"authorization": settings.FAST2SMS_API_KEY},
                data={"route": "otp", "variables_values": otp, "numbers": number},
            )
    except httpx.HTTPError as exc:
        raise OTPDeliveryError(f"SMS provider unreachable: {exc}") from exc

    body = {}
    try:
        body = resp.json()
    except ValueError:
        pass
    if resp.status_code != 200 or not body.get("return"):
        print(f"[OTP fast2sms error] {resp.status_code}: {resp.text[:300]}")
        raise OTPDeliveryError("SMS could not be sent. Please try again in a moment.")


async def _send_via_whatsapp(phone: str, otp: str) -> None:
    """WhatsApp Cloud API — sends an approved AUTHENTICATION template.
    Auth templates require the OTP both in the body ({{1}}) and in the
    copy-code button parameter.
    Docs: https://developers.facebook.com/docs/whatsapp/cloud-api"""
    url = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _whatsapp_number(phone),
        "type": "template",
        "template": {
            "name": settings.WHATSAPP_TEMPLATE_NAME,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": otp}]},
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": otp}],
                },
            ],
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise OTPDeliveryError(f"WhatsApp provider unreachable: {exc}") from exc

    if resp.status_code != 200:
        # Common causes: recipient not in the sandbox allow-list, template
        # not yet approved, or an expired temporary access token.
        print(f"[OTP whatsapp error] {resp.status_code}: {resp.text[:300]}")
        raise OTPDeliveryError("WhatsApp message could not be sent. Please try again in a moment.")


async def send_otp(phone: str, otp: str) -> None:
    """Send OTP via the configured provider.
    Raises OTPDeliveryError on delivery failure (mock never fails)."""
    provider = settings.OTP_PROVIDER

    if provider == "mock":
        print(f"\n{'='*50}")
        print(f"  [MOCK OTP] Phone: {phone}  |  OTP: {otp}")
        print(f"{'='*50}\n")
        return

    if provider == "fast2sms":
        if not settings.FAST2SMS_API_KEY:
            raise OTPDeliveryError("FAST2SMS_API_KEY is not configured.")
        await _send_via_fast2sms(phone, otp)
        return

    if provider == "whatsapp":
        if not (settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID):
            raise OTPDeliveryError("WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID are not configured.")
        await _send_via_whatsapp(phone, otp)
        return

    raise OTPDeliveryError(f"Unknown OTP provider '{provider}'.")
