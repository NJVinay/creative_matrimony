"""
Admin API — Platform management.
Trace: @context_documents/MVP_BACKLOG.md Epic J
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_roles as check_role
from app.models.user import User, UserRole
from app.models.profile import Profile, ProfilePhoto
from app.models.payment import UserSubscription
from app.models.audit import AuditLog

router = APIRouter(prefix="/admin", tags=["Admin"])

class AdminStats(BaseModel):
    total_users: int
    active_subscriptions: int
    pending_verifications: int

class UserListItem(BaseModel):
    id: int
    phone: str
    email: str | None
    role: UserRole
    is_banned: bool
    created_at: str

class PhoneOverrideIn(BaseModel):
    new_phone: str = Field(pattern=r'^\+?[1-9]\d{9,14}$')

@router.get("/stats", response_model=AdminStats)
async def get_stats(
    user: Annotated[User, Depends(check_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get high-level platform stats."""
    # Count Users
    user_count = await db.scalar(select(func.count(User.id)))
    
    # Count Active Subscriptions
    sub_count = await db.scalar(select(func.count(UserSubscription.id)).where(UserSubscription.is_active.is_(True)))
    
    # Count Pending Verifications (Profiles not verified / Photos pending)
    # We count ProfilePhotos where is_approved is None
    photo_count = await db.scalar(select(func.count(ProfilePhoto.id)).where(ProfilePhoto.is_approved.is_(None)))
    
    return {
        "total_users": user_count or 0,
        "active_subscriptions": sub_count or 0,
        "pending_verifications": photo_count
    }

@router.get("/users", response_model=List[UserListItem])
async def list_users(
    user: Annotated[User, Depends(check_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0
):
    """List users for management."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()
    return [
        UserListItem(
            id=u.id, 
            phone=u.phone, 
            email=u.email, 
            role=u.role, 
            is_banned=u.is_banned,
            created_at=u.created_at.isoformat()
        ) 
        for u in users
    ]

@router.patch("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    user: Annotated[User, Depends(check_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Ban a user."""
    await db.execute(update(User).where(User.id == user_id).values(is_banned=True))
    await db.commit()
    return {"status": "banned"}

@router.patch("/users/{user_id}/unban")
async def unban_user(
    user_id: int,
    user: Annotated[User, Depends(check_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Unban a user."""
    await db.execute(update(User).where(User.id == user_id).values(is_banned=False))
    await db.commit()
    return {"status": "unbanned"}

@router.patch("/users/{user_id}/phone")
async def override_phone(
    user_id: int,
    data: PhoneOverrideIn,
    request: Request,
    user: Annotated[User, Depends(check_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Admin override for user phone number."""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    existing = await db.scalar(select(User).where(User.phone == data.new_phone))
    if existing and existing.id != user_id:
        raise HTTPException(status_code=400, detail="Phone number already in use by another account.")
        
    old_phone = target.phone
    target.phone = data.new_phone
    
    db.add(AuditLog(
        user_id=user_id,
        action="admin_phone_override",
        resource_type="admin",
        ip_address=request.client.host if request.client else None,
        details={"admin_id": user.id, "old_phone": old_phone, "new_phone": data.new_phone}
    ))
    
    await db.commit()
    return {"status": "phone_updated", "new_phone": data.new_phone}
