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
from app.models.user import User, UserRole
from app.schemas.auth import (
    OTPRequestIn, OTPRequestOut, OTPVerifyIn, OTPVerifyOut,
    TokenRefreshIn, TokenRefreshOut, UserOut,
)
from app.services.otp_service import create_otp, is_on_cooldown, send_otp, verify_otp
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
    # Check cooldown
    if await is_on_cooldown(db, body.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait before requesting a new OTP.",
        )

    # Check if user is banned
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()
    if user and user.is_banned:
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    # Create and send OTP
    otp = await create_otp(db, body.phone)
    await send_otp(body.phone, otp)

    # Audit log
    db.add(AuditLog(
        user_id=user.id if user else None,
        action="otp_request",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
    ))

    response = OTPRequestOut(expires_in_seconds=settings.OTP_EXPIRE_SECONDS)
    return response


@router.post("/otp/verify", response_model=OTPVerifyOut)
@limiter.limit(settings.OTP_RATE_LIMIT_PER_IP)
async def verify_otp_endpoint(
    body: OTPVerifyIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify OTP and return JWT tokens. Creates user if first login."""
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
        user = User(
            phone=body.phone,
            role=UserRole.member,
            trial_started_at=datetime.now(timezone.utc),
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=30),
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
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
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
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return TokenRefreshOut(access_token=new_access)


@router.get("/me", response_model=UserOut)
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user info."""
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

