"""
Profile business logic — completion calculation, privacy enforcement.
Trace: @context_documents/MVP_BACKLOG.md Epic B + D,
       @context_documents/IDEA_PLANNER.md §2.2 + §2.4 + §3.2
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.user import User


# Fields required for "full access" per IDEA_PLANNER.md §3.2
COMPLETION_FIELDS = [
    "display_name",
    "gender",
    "date_of_birth",
    "bio",
    "city_village",
    "state",
    "religion_id",
    "community_id",
    "family_details",
    "partner_preferences",
]


def calculate_completion(profile: Profile) -> float:
    """Calculate profile completion percentage based on required fields."""
    filled = sum(1 for f in COMPLETION_FIELDS if getattr(profile, f, None) is not None)
    return round((filled / len(COMPLETION_FIELDS)) * 100, 1)


def calculate_age(dob: date) -> int:
    """Calculate age from date of birth."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Profile | None:
    """Get profile for a user."""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


async def get_profile_by_id(db: AsyncSession, profile_id: int) -> Profile | None:
    """Get profile by its own ID."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    return result.scalar_one_or_none()


def to_public_view(profile: Profile, user: User) -> dict:
    """Convert a profile to its privacy-safe public representation.
    Enforces: city/state only, no phone/email, age instead of DOB.
    Trace: @context_documents/IDEA_PLANNER.md §2.4
    """
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "gender": profile.gender.value if profile.gender else None,
        "age": calculate_age(profile.date_of_birth) if profile.date_of_birth else None,
        "bio": profile.bio,
        "city_village": profile.city_village,
        "state": profile.state,
        "religion_id": profile.religion_id,
        "community_id": profile.community_id,
        "education_level": profile.education_level,
        "occupation_category": profile.occupation_category,
        "marital_status": profile.marital_status.value if profile.marital_status else None,
        "is_verified": user.is_verified,
        "completion_pct": profile.completion_pct,
        "photo_blur_until_mutual": profile.photo_blur_until_mutual,
        # NEVER include: phone, email, date_of_birth, district_mandal, user_id
    }


def check_visibility(profile: Profile, viewer_user: User | None) -> bool:
    """Check if a profile is visible to the viewer.
    Trace: @context_documents/MVP_BACKLOG.md Epic D1
    """
    if profile.visibility.value == "hidden":
        return False
    if profile.visibility.value == "verified_only":
        if viewer_user is None or not viewer_user.is_verified:
            return False
    return True
