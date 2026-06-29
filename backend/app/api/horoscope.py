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
import shutil
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
    
    if not horoscope:
        # Return empty object or 404? 
        # Requirement F1: Optional fields. 
        # If no record, we can return 404 or just create one on fly?
        # Let's return 404 so frontend knows to show "Create" UI.
    if not horoscope:
        raise HTTPException(status_code=404, detail="Horoscope not found")
        
    return horoscope

@router.get("/profile/{profile_id}", response_model=HoroscopeOut)
async def get_public_horoscope(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get horoscope details for a public profile view."""
    result = await db.execute(select(Horoscope).where(Horoscope.profile_id == profile_id))
    horoscope = result.scalar_one_or_none()
    
    if not horoscope:
        raise HTTPException(status_code=404, detail="Horoscope not found")
        
    return horoscope

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

@router.post("/me/chart", response_model=HoroscopeOut)
async def upload_chart_image(
    file: UploadFile = File(...),
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Upload a horoscope chart image. MOCK implementation (local file)."""
    # 1. Ensure horoscope record exists
    result = await db.execute(select(Horoscope).where(Horoscope.profile_id == user.profile.id))
    horoscope = result.scalar_one_or_none()
    
    if not horoscope:
        horoscope = Horoscope(profile_id=user.profile.id)
        db.add(horoscope)
    
    # 2. Save file
    # We'll use static/uploads directory like ProfilePhoto
    UPLOAD_DIR = "static/uploads/horoscopes"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    filename = f"{user.id}_{uuid.uuid4()}.jpg" # Simple extension assumption
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 3. Update record
    # chart_images is a JSON list.
    current_images = list(horoscope.chart_images) if horoscope.chart_images else []
    # Mock URL
    url = f"/static/uploads/horoscopes/{filename}"
    current_images.append(url)
    
    # Update explicitly to trigger SQLAlchemy JSON detection?
    # Usually works if we re-assign.
    horoscope.chart_images = current_images
     # Need to ensure it's marked as modified if using mutable types?
    # Or just reassignment works.
    
    # Add if new
    if not horoscope.id:
        # db.add was called above
        pass

    await db.commit()
    await db.refresh(horoscope)
    
    return horoscope
