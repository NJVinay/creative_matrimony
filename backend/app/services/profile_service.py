"""
Profile business logic — completion calculation, privacy enforcement.
Trace: @context_documents/MVP_BACKLOG.md Epic B + D,
       @context_documents/IDEA_PLANNER.md §2.2 + §2.4 + §3.2
"""

from datetime import date, datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile, Gender
from app.models.user import User


# Legal minimum marriage age in India (Prohibition of Child Marriage Act, 2006):
# 18 for women, 21 for men. Any other gender gets the stricter bound.
MIN_MARRIAGE_AGE = {Gender.female: 18, Gender.male: 21}
DEFAULT_MIN_MARRIAGE_AGE = 21


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


def is_activatable(profile: Profile) -> bool:
    """A profile goes live with minimal fields (30%), and never below the legal
    marriage age (also deactivates legacy under-age profiles on their next edit)."""
    return profile.completion_pct >= 30.0 and meets_minimum_age(
        profile.date_of_birth, profile.gender
    )


async def get_profiles_by_user_ids(db: AsyncSession, user_ids) -> dict[int, Profile]:
    """Map user id → profile for the given users (users without one are absent)."""
    user_ids = {uid for uid in user_ids if uid is not None}
    if not user_ids:
        return {}
    result = await db.execute(select(Profile).where(Profile.user_id.in_(user_ids)))
    return {p.user_id: p for p in result.scalars().all()}


def calculate_age(dob: date) -> int:
    """Calculate age from date of birth."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def years_ago(years: int, today: date | None = None) -> date:
    """The date exactly `years` before today (29 Feb falls back to 28 Feb)."""
    today = today or date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


def minimum_age_for(gender) -> int:
    """Legal minimum marriage age for a gender (enum member or its string value)."""
    try:
        gender = Gender(gender)
    except ValueError:
        return DEFAULT_MIN_MARRIAGE_AGE
    return MIN_MARRIAGE_AGE.get(gender, DEFAULT_MIN_MARRIAGE_AGE)


def meets_minimum_age(dob: date | None, gender, today: date | None = None) -> bool:
    """True when someone born on `dob` has reached the legal marriage age."""
    if dob is None:
        return False
    return dob <= years_ago(minimum_age_for(gender), today)


def legal_age_condition(today: date | None = None):
    """SQL filter matching only profiles at or above the legal marriage age.
    Discovery surfaces (recommendations, search) must always apply it, so a
    minor's profile can never be shown, whatever the seeker's preferences."""
    clauses = [
        and_(Profile.gender == gender, Profile.date_of_birth <= years_ago(age, today))
        for gender, age in MIN_MARRIAGE_AGE.items()
    ]
    clauses.append(and_(
        Profile.gender.notin_(list(MIN_MARRIAGE_AGE)),
        Profile.date_of_birth <= years_ago(DEFAULT_MIN_MARRIAGE_AGE, today),
    ))
    return or_(*clauses)


async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Profile | None:
    """Get profile for a user."""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


async def get_profile_by_id(db: AsyncSession, profile_id: int) -> Profile | None:
    """Get profile by its own ID."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    return result.scalar_one_or_none()


def to_public_view(profile: Profile, user: User | None) -> dict:
    """Convert a profile to its privacy-safe public representation.
    Enforces: city/state only, no phone/email, age instead of DOB.
    `user` is the profile OWNER (for the is_verified badge); tolerates None.
    Trace: @context_documents/IDEA_PLANNER.md §2.4
    """
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "gender": profile.gender.value if profile.gender else None,
        "age": calculate_age(profile.date_of_birth) if profile.date_of_birth else None,
        "height_cm": profile.height_cm,
        "bio": profile.bio,
        "city_village": profile.city_village,
        "state": profile.state,
        "religion_id": profile.religion_id,
        "community_id": profile.community_id,
        "education_level": profile.education_level,
        "occupation_category": profile.occupation_category,
        "marital_status": profile.marital_status.value if profile.marital_status else None,
        "is_verified": bool(user.is_verified) if user else False,
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
