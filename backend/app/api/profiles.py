"""
Profile API — create, read, update, privacy controls.
Trace: @context_documents/MVP_BACKLOG.md Epic B + D,
       @context_documents/IDEA_PLANNER.md §2.2 + §2.4
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.profile import Profile, ProfileMode, Gender, Visibility, MaritalStatus
from app.models.user import User
from app.schemas.profile import (
    ProfileCreateIn, ProfileUpdateIn, PrivacyUpdateIn,
    ProfileOut, ProfilePublicOut,
)
from app.services.profile_service import (
    calculate_completion, get_profile_by_user_id, get_profile_by_id,
    to_public_view, check_visibility,
)

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new profile (self or parent-managed). One profile per user."""
    existing = await get_profile_by_user_id(db, user.id)
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists for this user.")

    profile = Profile(
        user_id=user.id,
        profile_mode=ProfileMode(body.profile_mode),
        guardian_relationship=body.guardian_relationship,
        display_name=body.display_name,
        gender=Gender(body.gender),
        date_of_birth=body.date_of_birth,
        bio=body.bio,
        city_village=body.city_village,
        state=body.state,
        country=body.country,
        religion_id=body.religion_id,
        community_id=body.community_id,
        subcaste_id=body.subcaste_id,
        education_level=body.education_level,
        occupation_category=body.occupation_category,
        marital_status=MaritalStatus(body.marital_status) if body.marital_status else None,
        identity_language_group=body.identity_language_group,
        family_details=body.family_details,
        partner_preferences=body.partner_preferences,
    )
    profile.completion_pct = calculate_completion(profile)
    profile.is_active = profile.completion_pct >= 30.0  # Activate with minimal fields

    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the current user's own profile with full details."""
    profile = await get_profile_by_user_id(db, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create one first.")
    return profile


@router.patch("/me", response_model=ProfileOut)
async def update_my_profile(
    body: ProfileUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update the current user's profile. Recalculates completion %."""
    profile = await get_profile_by_user_id(db, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "marital_status" and value is not None:
            setattr(profile, field, MaritalStatus(value))
        else:
            setattr(profile, field, value)

    profile.completion_pct = calculate_completion(profile)
    profile.is_active = profile.completion_pct >= 30.0

    await db.flush()
    await db.refresh(profile)
    return profile


@router.patch("/me/privacy", response_model=ProfileOut)
async def update_privacy(
    body: PrivacyUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update privacy settings: visibility mode, photo blur, hide-from-search."""
    profile = await get_profile_by_user_id(db, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    if body.visibility is not None:
        profile.visibility = Visibility(body.visibility)
    if body.photo_blur_until_mutual is not None:
        profile.photo_blur_until_mutual = body.photo_blur_until_mutual
    if body.hide_from_search is not None:
        profile.hide_from_search = body.hide_from_search

    await db.flush()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfilePublicOut)
async def get_public_profile(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Get a profile's public view.
    Enforces: visibility rules, verified-only constraint, location privacy.
    NEVER exposes phone, email, or precise location.
    """
    profile = await get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    # Check visibility rules
    if not check_visibility(profile, user):
        raise HTTPException(status_code=403, detail="This profile is not visible to you.")

    # Get profile owner for is_verified flag
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == profile.user_id))
    profile_owner = result.scalar_one_or_none()

    return ProfilePublicOut(**to_public_view(profile, profile_owner))
