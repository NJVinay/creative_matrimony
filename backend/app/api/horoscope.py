"""
Horoscope API endpoints.
Trace: @context_documents/MVP_BACKLOG.md Epic F
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile, ProfilePhoto # borrowing storage logic?
from app.models.horoscope import Horoscope
from app.schemas.horoscope import HoroscopeOut, HoroscopeUpdate, HoroscopeCreate
from app.middleware.auth import get_current_user
from app.services.profile_service import get_profile_for_viewer, can_view_photos
from app.config import settings
import os
import uuid

router = APIRouter(prefix="/horoscope", tags=["Horoscope"])

@router.get("/me", response_model=HoroscopeOut)
async def get_my_horoscope(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get the current user's horoscope details."""
    result = await db.execute(select(Horoscope).where(Horoscope.profile_id == user.profile.id))
    horoscope = result.scalar_one_or_none()

    # Requirement F1: fields are optional — a 404 tells the frontend to show the "Create" UI.
    if not horoscope:
        raise HTTPException(status_code=404, detail="Horoscope not found")

    return horoscope

@router.get("/profile/{profile_id}", response_model=HoroscopeOut)
async def get_public_horoscope(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Get horoscope details for a profile the requester is allowed to see.
    Chart images follow the owner's photo blur: withheld until mutual interest."""
    profile = await get_profile_for_viewer(db, profile_id, user)

    result = await db.execute(select(Horoscope).where(Horoscope.profile_id == profile_id))
    horoscope = result.scalar_one_or_none()
    if not horoscope:
        raise HTTPException(status_code=404, detail="Horoscope not found")

    out = HoroscopeOut.model_validate(horoscope)
    if out.chart_images and not await can_view_photos(db, user, profile):
        out = out.model_copy(update={"chart_images": [], "charts_locked": True})
    return out

@router.put("/me", response_model=HoroscopeOut)
async def update_my_horoscope(
    data: HoroscopeUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Create or update horoscope details."""
    # Check if exists
    result = await db.execute(select(Horoscope).where(Horoscope.profile_id == user.profile.id))
    horoscope = result.scalar_one_or_none()
    
    if not horoscope:
        # Create
        horoscope = Horoscope(**data.model_dump(), profile_id=user.profile.id)
        db.add(horoscope)
        await db.commit()
        await db.refresh(horoscope)
    else:
        # Update
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(horoscope, key, value)
        await db.commit()
        await db.refresh(horoscope)
        
    return horoscope

ALLOWED_CHART_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_CHART_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/me/chart", response_model=HoroscopeOut)
async def upload_chart_image(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Upload a horoscope chart image (stored privately under LOCAL_STORAGE_DIR)."""
    if file.content_type not in ALLOWED_CHART_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(ALLOWED_CHART_TYPES)}",
        )
    contents = await file.read()
    if len(contents) > MAX_CHART_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5 MB.")

    # 1. Ensure horoscope record exists
    result = await db.execute(select(Horoscope).where(Horoscope.profile_id == user.profile.id))
    horoscope = result.scalar_one_or_none()

    if not horoscope:
        horoscope = Horoscope(profile_id=user.profile.id)
        db.add(horoscope)

    # 2. Save under the same storage root the app serves at /uploads
    upload_dir = os.path.join(settings.LOCAL_STORAGE_DIR, "horoscopes")
    os.makedirs(upload_dir, exist_ok=True)

    ext = ALLOWED_CHART_TYPES[file.content_type]
    filename = f"{user.id}_{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(upload_dir, filename), "wb") as buffer:
        buffer.write(contents)

    # 3. Append to the JSON list (re-assign so SQLAlchemy detects the change)
    current_images = list(horoscope.chart_images) if horoscope.chart_images else []
    current_images.append(f"/uploads/horoscopes/{filename}")
    horoscope.chart_images = current_images

    await db.commit()
    await db.refresh(horoscope)

    return horoscope
