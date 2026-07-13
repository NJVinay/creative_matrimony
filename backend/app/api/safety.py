"""
Safety API — panic block (block/unblock/list).
Blocks are addressed by PROFILE id (public views never expose user ids).
Trace: @context_documents/SAFETY_TRUST_PLANNER.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.audit import AuditLog
from app.models.profile import Profile
from app.models.safety import UserBlock
from app.models.user import User
from app.services.safety_service import block_user, unblock_user

router = APIRouter(prefix="/safety", tags=["Safety"])


class BlockIn(BaseModel):
    reason: str | None = Field(None, max_length=1000)


class BlockedProfileOut(BaseModel):
    profile_id: int | None
    display_name: str | None
    blocked_at: str


async def _resolve_target_user(db: AsyncSession, profile_id: int) -> int:
    target_user_id = await db.scalar(select(Profile.user_id).where(Profile.id == profile_id))
    if not target_user_id:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return target_user_id


@router.post("/block/{profile_id}", status_code=status.HTTP_201_CREATED)
async def panic_block(
    profile_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: BlockIn | None = None,
):
    """Panic block: immediately hides both profiles from each other,
    closes shared chats, and declines pending interests."""
    target_user_id = await _resolve_target_user(db, profile_id)
    if target_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot block yourself.")

    await block_user(db, user.id, target_user_id, body.reason if body else None)

    db.add(AuditLog(
        user_id=user.id,
        action="panic_block",
        resource_type="user",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
    ))
    return {"status": "blocked"}


@router.delete("/block/{profile_id}")
async def remove_block(
    profile_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a block the caller previously created."""
    target_user_id = await _resolve_target_user(db, profile_id)
    removed = await unblock_user(db, user.id, target_user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="No block found for this profile.")
    return {"status": "unblocked"}


@router.get("/blocks", response_model=list[BlockedProfileOut])
async def list_my_blocks(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List profiles the caller has blocked."""
    result = await db.execute(
        select(UserBlock, Profile)
        .outerjoin(Profile, Profile.user_id == UserBlock.blocked_user_id)
        .where(UserBlock.blocker_user_id == user.id)
        .order_by(UserBlock.created_at.desc())
    )
    return [
        BlockedProfileOut(
            profile_id=profile.id if profile else None,
            display_name=profile.display_name if profile else None,
            blocked_at=block.created_at.isoformat(),
        )
        for block, profile in result.all()
    ]
