"""
OTP service — generation, hashing, verification, and sending.
Providers: mock (console log), fast2sms (India SMS), whatsapp (Cloud API).
Trace: @context_documents/BACKEND_PLANNER.md §1, @context_documents/SECURITY_PLANNER.md §2

Throttling model. Each code is bound to the browser that requested it (its
otp_device cookie), and only that browser can check it, so guesses from anyone
else never use up the owner's code. Per phone:
  - one code per OTP_RESEND_SECONDS per device (only a device's own requests
    start its window, so nobody can hold up someone else's request);
  - devices that have never logged in to the phone share OTP_MAX_SENDS_PER_HOUR
    codes an hour, which bounds guessing (and SMS volume) however many IPs or
    devices an attacker uses. Devices that have logged in to the phone before
    are exempt, so a stranger can never lock the owner's browser out.
Requests for one phone are serialised (lock_phone), so parallel requests cannot
slip past either limit.
"""

import enum
import hashlib
import hmac
import math
import random
import re
import secrets
import string
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import OTPLog, OTPPhoneLock

# httpOnly cookie naming the browser a code was sent from (see device_hash)
OTP_DEVICE_COOKIE = "otp_device"
_DEVICE_ID_RE = re.compile(r"[A-Za-z0-9_-]{32,128}")
# Rolling window of OTP_MAX_SENDS_PER_HOUR
_SEND_CAP_WINDOW = timedelta(hours=1)


class OTPDeliveryError(RuntimeError):
    """Raised when the configured provider could not deliver the OTP.
    The API layer turns this into a clean 502 so the client can retry
    (the DB transaction rolls back, so no resend window is burned)."""


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


def _seconds_until(moment: datetime) -> int:
    """Whole seconds from now until `moment`, rounded up (0 if past)."""
    return max(0, math.ceil((moment - _now_utc()).total_seconds()))


def new_device_id() -> str:
    """A fresh otp_device cookie value (random, unguessable)."""
    return secrets.token_urlsafe(32)


def device_hash(device_id: str | None) -> str | None:
    """What OTPLog stores for a device: sha256 of a well-formed otp_device
    value, or None when the request carried no (or a malformed) cookie."""
    if not device_id or not _DEVICE_ID_RE.fullmatch(device_id):
        return None
    return hashlib.sha256(device_id.encode()).hexdigest()


async def lock_phone(db: AsyncSession, phone: str) -> None:
    """Serialise OTP requests for one phone until this transaction ends, so
    the throttle checks and the new code's insert are atomic (parallel
    requests would otherwise all pass the checks before any insert).
    Row lock on otp_phone_locks in PostgreSQL; SQLite locks the database on
    the insert. Must run before the checks; the commit or rollback releases it."""
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    await db.execute(insert(OTPPhoneLock).values(phone=phone).on_conflict_do_nothing())
    await db.execute(
        update(OTPPhoneLock).where(OTPPhoneLock.phone == phone).values(locked_at=_now_utc())
    )


async def get_active_otp(db: AsyncSession, phone: str, device: str) -> OTPLog | None:
    """The newest unexpired, unverified code sent to `phone` for this device."""
    cutoff = _now_utc() - timedelta(seconds=settings.OTP_EXPIRE_SECONDS)
    result = await db.execute(
        select(OTPLog)
        .where(
            OTPLog.phone == phone,
            OTPLog.device_hash == device,
            OTPLog.verified_at.is_(None),
            OTPLog.created_at >= cutoff,
        )
        .order_by(OTPLog.created_at.desc(), OTPLog.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resend_remaining_seconds(db: AsyncSession, phone: str, device: str | None) -> int:
    """
    Seconds until this device may be sent another code for this phone (0 = now).

    One code per OTP_RESEND_SECONDS per (phone, device). Only the device's own
    requests start its window, so a stranger requesting codes for the number
    never holds up the owner. A request without a device cookie has no window
    of its own; phone_cap_remaining_seconds bounds those. Codes already used
    to log in don't count, so a member can log out and straight back in.
    """
    if device is None:
        return 0
    last_sent = await db.scalar(
        select(func.max(OTPLog.created_at)).where(
            OTPLog.phone == phone,
            OTPLog.device_hash == device,
            OTPLog.verified_at.is_(None),
        )
    )
    if last_sent is None:
        return 0
    return _seconds_until(_naive_utc(last_sent) + timedelta(seconds=settings.OTP_RESEND_SECONDS))


def _known_devices(phone: str):
    """Devices that have logged in to `phone` (a verified code), as a subquery."""
    return select(OTPLog.device_hash).where(
        OTPLog.phone == phone,
        OTPLog.verified_at.is_not(None),
        OTPLog.device_hash.is_not(None),
    )


async def is_known_device(db: AsyncSession, phone: str, device: str | None) -> bool:
    """Has this device logged in to this phone before?"""
    if device is None:
        return False
    found = await db.scalar(
        select(OTPLog.id).where(
            OTPLog.phone == phone,
            OTPLog.device_hash == device,
            OTPLog.verified_at.is_not(None),
        ).limit(1)
    )
    return found is not None


async def phone_cap_remaining_seconds(db: AsyncSession, phone: str, device: str | None) -> int:
    """
    Seconds until this device may be sent a code under the per-phone cap (0 = now).

    Devices that have never logged in to the phone share OTP_MAX_SENDS_PER_HOUR
    codes per rolling hour. With OTP_MAX_ATTEMPTS checks per code, that caps
    guessing at their product per phone per hour, however many IPs or fresh
    devices are used, and caps the SMS a stranger can trigger. A device that
    has logged in to the phone before is exempt (only its resend window
    applies), so using up the cap never locks the owner's browser out.
    """
    if await is_known_device(db, phone, device):
        return 0
    sent = (await db.scalars(
        select(OTPLog.created_at)
        .where(
            OTPLog.phone == phone,
            OTPLog.created_at >= _now_utc() - _SEND_CAP_WINDOW,
            or_(OTPLog.device_hash.is_(None), OTPLog.device_hash.notin_(_known_devices(phone))),
        )
        .order_by(OTPLog.created_at)
    )).all()
    over = len(sent) - settings.OTP_MAX_SENDS_PER_HOUR
    if over < 0:
        return 0
    # Wait until enough of the oldest codes leave the window to get under the cap
    return max(1, _seconds_until(_naive_utc(sent[over]) + _SEND_CAP_WINDOW))


async def create_otp(db: AsyncSession, phone: str, device: str) -> str:
    """Generate and store a new code for `phone`, checkable only by `device`
    (a device_hash). Returns the raw OTP (for sending)."""
    otp = _generate_otp(settings.OTP_LENGTH)
    otp_log = OTPLog(
        phone=phone,
        otp_hash=_hash_otp(otp),
        attempts=0,
        device_hash=device,
    )
    db.add(otp_log)
    await db.flush()
    return otp


class OTPCheck(str, enum.Enum):
    """Outcome of verify_otp."""
    verified = "verified"
    invalid = "invalid"      # wrong code, or no unexpired unused code for this phone + device
    exhausted = "exhausted"  # this device's current code has used all OTP_MAX_ATTEMPTS checks


async def verify_otp(db: AsyncSession, phone: str, otp: str, device: str | None) -> OTPCheck:
    """
    Check `otp` against the newest unexpired, unused code this device
    requested for the phone. Without a device (no otp_device cookie) nothing
    is checked.

    A code allows at most OTP_MAX_ATTEMPTS checks, however many requests race:
    each check is reserved with one conditional UPDATE (attempts = attempts + 1
    in SQL, only while attempts < max) BEFORE the hash is compared, so parallel
    guesses cannot all read a stale count. Codes per phone are capped (see the
    module docstring), which bounds guessing per phone.

    Only the requesting device can check a code, so a stranger's wrong guesses
    for someone's number never touch the owner's code. Wrong guesses only burn
    the code they were made against: the next code gets its own budget, so a
    typo on an old, abandoned code never counts against a later login.

    The caller must commit on failure too, or the reserved check rolls back.
    """
    if device is None:
        return OTPCheck.invalid
    otp_log = await get_active_otp(db, phone, device)
    if not otp_log:
        return OTPCheck.invalid

    attempts = await db.scalar(
        update(OTPLog)
        .where(
            OTPLog.id == otp_log.id,
            OTPLog.verified_at.is_(None),
            func.coalesce(OTPLog.attempts, 0) < settings.OTP_MAX_ATTEMPTS,
        )
        .values(attempts=func.coalesce(OTPLog.attempts, 0) + 1)
        .returning(OTPLog.attempts)
        .execution_options(synchronize_session=False)
    )
    if attempts is None:
        # No checks left — or a parallel request just used the code to log in
        used = await db.scalar(select(OTPLog.verified_at).where(OTPLog.id == otp_log.id))
        return OTPCheck.invalid if used else OTPCheck.exhausted

    if not hmac.compare_digest(_hash_otp(otp), otp_log.otp_hash):
        return OTPCheck.exhausted if attempts >= settings.OTP_MAX_ATTEMPTS else OTPCheck.invalid

    # Claim the code atomically, so one code logs in only once
    claimed = await db.execute(
        update(OTPLog)
        .where(OTPLog.id == otp_log.id, OTPLog.verified_at.is_(None))
        .values(verified_at=_now_utc())
        .execution_options(synchronize_session=False)
    )
    return OTPCheck.verified if claimed.rowcount == 1 else OTPCheck.invalid


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
