"""
Profile photo upload + admin moderation.
Trace: @context_documents/MVP_BACKLOG.md Epic D, F
"""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models.profile import Profile, ProfilePhoto
from app.models.user import User, UserRole
from app.schemas.profile import ProfilePhotoOut
from app.services.profile_service import get_profile_for_viewer, can_view_photos

router = APIRouter(prefix="/profiles", tags=["Photos"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/me/photos", response_model=ProfilePhotoOut, status_code=status.HTTP_201_CREATED)
async def upload_my_photo(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    is_primary: bool = False,
):
    """Upload a profile photo. Photos start as pending (is_approved=NULL) for moderation."""
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Read & validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5 MB.")

    # Find or create user profile
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Create a profile first before uploading photos.")

    # Save to local storage
    storage_dir = os.path.join(settings.LOCAL_STORAGE_DIR, "profiles")
    os.makedirs(storage_dir, exist_ok=True)
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        ext = "jpg"
    storage_key = f"profile_{user.id}_{uuid.uuid4().hex}.{ext}"
    abs_path = os.path.join(storage_dir, storage_key)
    with open(abs_path, "wb") as f:
        f.write(contents)

    # If marked primary, demote others
    if is_primary:
        existing = await db.execute(
            select(ProfilePhoto).where(ProfilePhoto.profile_id == profile.id)
        )
        for photo in existing.scalars().all():
            photo.is_primary = False

    photo = ProfilePhoto(
        profile_id=profile.id,
        storage_key=f"uploads/profiles/{storage_key}",
        is_primary=is_primary,
        is_approved=None,  # Pending moderation
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)
    return photo


@router.get("/me/photos", response_model=list[ProfilePhotoOut])
async def list_my_photos(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all photos for the current user's profile."""
    result = await db.execute(
        select(ProfilePhoto)
        .join(Profile, Profile.id == ProfilePhoto.profile_id)
        .where(Profile.user_id == user.id)
        .order_by(ProfilePhoto.is_primary.desc(), ProfilePhoto.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{profile_id}/photos", response_model=list[ProfilePhotoOut])
async def list_profile_photos(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """List approved photos for a profile the requester is allowed to see.
    Photo blur is enforced here, not just in the UI: until mutual interest the
    photos come back locked (storage_key=None, locked=True), so the viewer
    learns how many there are but never gets the file URLs."""
    profile = await get_profile_for_viewer(db, profile_id, user)

    result = await db.execute(
        select(ProfilePhoto)
        .where(
            ProfilePhoto.profile_id == profile_id,
            ProfilePhoto.is_approved.is_(True),
        )
        .order_by(ProfilePhoto.is_primary.desc(), ProfilePhoto.created_at.desc())
    )
    photos = [ProfilePhotoOut.model_validate(p) for p in result.scalars().all()]
    if photos and not await can_view_photos(db, user, profile):
        photos = [p.model_copy(update={"storage_key": None, "locked": True}) for p in photos]
    return photos


# ── Admin moderation ──────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/photos",
    tags=["Admin – Photos"],
    dependencies=[Depends(require_roles(UserRole.admin, UserRole.moderator))],
)


@admin_router.get("/pending", response_model=list[ProfilePhotoOut])
async def list_pending_photos(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all photos awaiting moderation (is_approved IS NULL)."""
    result = await db.execute(
        select(ProfilePhoto)
        .where(ProfilePhoto.is_approved.is_(None))
        .order_by(ProfilePhoto.created_at.asc())
    )
    return result.scalars().all()


@admin_router.patch("/{photo_id}/approve", response_model=ProfilePhotoOut)
async def approve_photo(
    photo_id: int,
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.moderator))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Approve a pending photo."""
    result = await db.execute(select(ProfilePhoto).where(ProfilePhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found.")
    photo.is_approved = True
    photo.reviewed_by = user.id
    photo.rejection_reason = None
    await db.flush()
    await db.refresh(photo)
    return photo


@admin_router.patch("/{photo_id}/reject", response_model=ProfilePhotoOut)
async def reject_photo(
    photo_id: int,
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.moderator))],
    db: Annotated[AsyncSession, Depends(get_db)],
    reason: str = "",
):
    """Reject a pending photo with a reason."""
    result = await db.execute(select(ProfilePhoto).where(ProfilePhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found.")
    photo.is_approved = False
    photo.reviewed_by = user.id
    photo.rejection_reason = reason or "Inappropriate content"
    await db.flush()
    await db.refresh(photo)
    return photo
