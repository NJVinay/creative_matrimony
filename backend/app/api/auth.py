"""
Auth API — OTP request, verify, refresh, logout.
Trace: @context_documents/MVP_BACKLOG.md Epic A, @context_documents/SECURITY_PLANNER.md §2
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import (
    create_access_token, create_refresh_token, decode_token, get_current_user,
)
from app.models.audit import AuditLog
from app.models.safety import BannedPhone
from app.models.user import User, UserRole
from app.schemas.auth import (
    ContactUpdateIn, OTPRequestIn, OTPRequestOut, OTPVerifyIn, OTPVerifyOut,
    TokenRefreshIn, TokenRefreshOut, UserOut,
)
from app.services.otp_service import (
    OTP_DEVICE_COOKIE, OTPCheck, OTPDeliveryError, create_otp, device_hash, lock_phone,
    new_device_id, phone_cap_remaining_seconds, resend_remaining_seconds, send_otp, verify_otp,
)
from app.rate_limit import limiter
from app.models.user import RevokedToken

router = APIRouter(prefix="/auth", tags=["Authentication"])

# The otp_device cookie outlives any one login: a device that has logged in to
# a phone stays exempt from that phone's OTP_MAX_SENDS_PER_HOUR cap
OTP_DEVICE_COOKIE_MAX_AGE = 365 * 24 * 3600


def _wait_text(seconds: int) -> str:
    """Human wait time for 429 messages: '45 seconds', '10 minutes'."""
    if seconds < 90:
        return f"{seconds} second{'' if seconds == 1 else 's'}"
    return f"{math.ceil(seconds / 60)} minutes"


def _too_many(detail: str, wait_seconds: int) -> HTTPException:
    """429 that says how long to wait, in the message and Retry-After."""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(wait_seconds)},
    )


def _code_used_up(resend_in: int) -> HTTPException:
    """429 once a code has had OTP_MAX_ATTEMPTS checks: only that code is dead,
    a new one can be requested as soon as this device's limits allow."""
    when = f" in {_wait_text(resend_in)}" if resend_in else ""
    return _too_many(
        f"Too many incorrect attempts for this code. Please request a new OTP{when}.",
        resend_in,
    )


def _device_id(request: Request) -> str | None:
    """The request's otp_device cookie, if well-formed."""
    value = request.cookies.get(OTP_DEVICE_COOKIE)
    return value if device_hash(value) else None


def _set_device_cookie(response: Response, device_id: str) -> None:
    """httpOnly, like the auth cookies, and sent only to the OTP endpoints."""
    response.set_cookie(
        key=OTP_DEVICE_COOKIE,
        value=device_id,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=OTP_DEVICE_COOKIE_MAX_AGE,
        path=f"{settings.API_PREFIX}{router.prefix}/otp",
    )


async def _next_send_wait(db: AsyncSession, phone: str, device: str | None) -> int:
    """Seconds until this device may be sent another code for the phone."""
    return max(
        await resend_remaining_seconds(db, phone, device),
        await phone_cap_remaining_seconds(db, phone, device),
    )


@router.post("/otp/request", response_model=OTPRequestOut)
@limiter.limit(settings.OTP_RATE_LIMIT_PER_IP)
async def request_otp(
    body: OTPRequestIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send OTP to phone number. Throttled per phone + device, per phone for
    devices new to it, and per IP. The code is bound to this browser's
    otp_device cookie (set here if missing): only this browser can check it."""
    # Ban evasion (Epic J2): phones of permanently banned users cannot re-enter,
    # whether or not a user record still exists. The attempt itself is flagged.
    banned_phone = await db.scalar(select(BannedPhone).where(BannedPhone.phone == body.phone))
    if banned_phone:
        db.add(AuditLog(
            user_id=banned_phone.user_id,
            action="ban_evasion_attempt",
            resource_type="auth",
            ip_address=request.client.host if request.client else None,
            details={"phone": body.phone},
        ))
        # Commit now — the HTTPException below would roll this back otherwise
        await db.commit()
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    # Check if user is banned (covers bans without a blocklist entry)
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()
    if user and user.is_banned:
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    # Throttles, checked and recorded atomically per phone (parallel requests
    # wait here). Wrong codes never block a new request — they only burn the
    # code they were typed against (verify_otp)
    device_id = _device_id(request)
    device = device_hash(device_id)
    await lock_phone(db, body.phone)
    resend_in = await resend_remaining_seconds(db, body.phone, device)
    if resend_in:
        raise _too_many(
            f"Please wait {_wait_text(resend_in)} before requesting a new OTP.",
            resend_in,
        )
    cap_in = await phone_cap_remaining_seconds(db, body.phone, device)
    if cap_in:
        raise _too_many(
            f"Too many OTPs were requested for this number. Please try again in {_wait_text(cap_in)}.",
            cap_in,
        )

    # Create and send OTP, bound to this browser
    if device_id is None:
        device_id = new_device_id()
        device = device_hash(device_id)
    otp = await create_otp(db, body.phone, device)
    try:
        await send_otp(body.phone, otp)
    except OTPDeliveryError as exc:
        # Raising rolls back the OTPLog insert, so the failed attempt
        # does not count against the resend window or the cap — the user can retry.
        raise HTTPException(status_code=502, detail=str(exc))
    _set_device_cookie(response, device_id)

    # Audit log
    db.add(AuditLog(
        user_id=user.id if user else None,
        action="otp_request",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
    ))

    return OTPRequestOut(
        expires_in_seconds=settings.OTP_EXPIRE_SECONDS,
        resend_after_seconds=settings.OTP_RESEND_SECONDS,
        # Testing aid — no SMS provider is integrated yet; the frontend
        # displays this in a toast when present. Off in production.
        dev_otp=otp if settings.OTP_DEV_ECHO else None,
    )


@router.post("/otp/verify", response_model=OTPVerifyOut)
@limiter.limit(settings.OTP_RATE_LIMIT_PER_IP)
async def verify_otp_endpoint(
    body: OTPVerifyIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify OTP and return JWT tokens. Creates user if first login."""
    # Ban evasion (Epic J2): reject even if an OTP was issued pre-ban.
    banned_phone = await db.scalar(select(BannedPhone).where(BannedPhone.phone == body.phone))
    if banned_phone:
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    # Only the browser that requested the code can check it (otp_device cookie)
    device_id = _device_id(request)
    device = device_hash(device_id)
    check = await verify_otp(db, body.phone, body.otp, device)
    if check is not OTPCheck.verified:
        # Commit now — the HTTPException below would roll back the reserved
        # check, leaving wrong guesses unlimited
        await db.commit()
        if check is OTPCheck.exhausted:
            raise _code_used_up(await _next_send_wait(db, body.phone, device))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP.",
        )

    # Find or create user
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        # Naive UTC — asyncpg rejects tz-aware values for timestamp columns
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = User(
            phone=body.phone,
            role=UserRole.member,
            trial_started_at=now,
            trial_ends_at=now + timedelta(days=30),
        )
        db.add(user)
        await db.flush()

    # Generate tokens
    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action="otp_verify_success",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
        details={"is_new_user": is_new},
    ))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )
    # Renew it: this device is now known to the phone (exempt from the send cap)
    _set_device_cookie(response, device_id)

    return OTPVerifyOut(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=is_new,
    )


@router.post("/refresh", response_model=TokenRefreshOut)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: TokenRefreshIn = None,
):
    """Refresh an access token using a valid refresh token."""
    refresh_token = request.cookies.get("refresh_token") or (body.refresh_token if body else None)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
        
    jti = payload.get("jti")
    if jti:
        revoked = await db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked:
            raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account is banned")

    new_access = create_access_token(user.id, user.role.value)
    
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return TokenRefreshOut(access_token=new_access)


@router.get("/me", response_model=UserOut)
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user info."""
    return user


@router.patch("/me/contact", response_model=UserOut)
async def update_contact(
    body: ContactUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Set email and weekly-digest consent (Epic G2 — consent-gated)."""
    if body.email is not None:
        existing = await db.scalar(
            select(User).where(User.email == body.email, User.id != user.id)
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use.")
        user.email = body.email
    if body.email_digest_opt_in is not None:
        if body.email_digest_opt_in and not (user.email or body.email):
            raise HTTPException(status_code=400, detail="Add an email address to enable the digest.")
        user.email_digest_opt_in = body.email_digest_opt_in
    await db.flush()
    await db.refresh(user)
    return user

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)]
):
    """Revoke the refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                revoked = await db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
                if not revoked:
                    db.add(RevokedToken(jti=jti))
                    await db.commit()
        except Exception:
            pass
            
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "logged_out"}

