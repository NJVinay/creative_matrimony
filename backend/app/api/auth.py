"""
Auth API — OTP request, verify, refresh, logout.
Trace: @context_documents/MVP_BACKLOG.md Epic A, @context_documents/SECURITY_PLANNER.md §2
"""

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
    OTPDeliveryError, create_otp, is_on_cooldown, send_otp, verify_otp,
)
from app.rate_limit import limiter
from app.models.user import RevokedToken

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/otp/request", response_model=OTPRequestOut)
@limiter.limit(settings.OTP_RATE_LIMIT_PER_IP)
async def request_otp(
    body: OTPRequestIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send OTP to phone number. Rate-limited per phone and IP."""
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

    # Check cooldown
    if await is_on_cooldown(db, body.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait before requesting a new OTP.",
        )

    # Create and send OTP
    otp = await create_otp(db, body.phone)
    try:
        await send_otp(body.phone, otp)
    except OTPDeliveryError as exc:
        # Raising rolls back the OTPLog insert, so the failed attempt
        # does not start the per-phone cooldown — the user can retry.
        raise HTTPException(status_code=502, detail=str(exc))

    # Audit log
    db.add(AuditLog(
        user_id=user.id if user else None,
        action="otp_request",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
    ))

    return OTPRequestOut(
        expires_in_seconds=settings.OTP_EXPIRE_SECONDS,
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

    if not await verify_otp(db, body.phone, body.otp):
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

