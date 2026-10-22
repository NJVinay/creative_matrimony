"""
Profile business logic — completion calculation, privacy enforcement.
Trace: @context_documents/MVP_BACKLOG.md Epic B + D,
       @context_documents/IDEA_PLANNER.md §2.2 + §2.4 + §3.2
"""

from datetime import date, datetime, timezone
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, func, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import Interest, InterestStatus
from app.models.profile import Profile, ProfilePhoto, Gender, Visibility
from app.models.user import User, UserRole


# Staff who review reported members: they may open any profile (hidden,
# verified-only, blocked, under-age) and its photos, so reports can be acted on.
REVIEWER_ROLES = frozenset({UserRole.admin, UserRole.moderator})


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


def visibility_condition(viewer_user: User | None):
    """SQL form of check_visibility, for discovery queries: never hidden
    profiles, and verified-only ones only for verified viewers."""
    if viewer_user is not None and viewer_user.is_verified:
        return Profile.visibility != Visibility.hidden
    return Profile.visibility == Visibility.public


def is_reviewer(user: User | None) -> bool:
    """Admins and moderators review reports, so privacy rules never hide a member from them."""
    return user is not None and user.role in REVIEWER_ROLES


async def is_underage_viewer(db: AsyncSession, viewer_user: User | None) -> bool:
    """True for a member (not staff) whose own profile is below the legal
    marriage age: a legacy row from before the DOB check. Such members see no
    other member anywhere (profiles, photos, charts, search, matches,
    interests), whether or not the under-age cleanup has run, and whatever
    interests they had accepted before. Same age rule as discovery."""
    if viewer_user is None or is_reviewer(viewer_user):
        return False
    found = await db.scalar(
        select(Profile.id)
        .where(Profile.user_id == viewer_user.id, not_(legal_age_condition()))
        .limit(1)
    )
    return found is not None


async def get_profile_for_viewer(db: AsyncSession, profile_id: int, viewer_user: User) -> Profile:
    """Load a profile on behalf of `viewer_user`, or raise the HTTP error to return.
    Single gate for the profile, photos and horoscope endpoints:
    - under the legal marriage age (legacy rows) → 404, as if it did not exist
    - a viewer under the legal marriage age (legacy rows) → 403, for any profile
    - visibility rules or a block in either direction → 403
    Admins and moderators bypass all of these to review reported profiles.
    """
    profile = await get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    if is_reviewer(viewer_user):
        return profile

    if not meets_minimum_age(profile.date_of_birth, profile.gender):
        raise HTTPException(status_code=404, detail="Profile not found.")
    if await is_underage_viewer(db, viewer_user):
        raise HTTPException(
            status_code=403,
            detail="Profiles are available only to members of the legal marriage age.",
        )
    if not check_visibility(profile, viewer_user):
        raise HTTPException(status_code=403, detail="This profile is not visible to you.")

    # Blocked users (either direction) can never see each other
    from app.services.safety_service import are_blocked
    if await are_blocked(db, viewer_user.id, profile.user_id):
        raise HTTPException(status_code=403, detail="This profile is not visible to you.")
    return profile


async def photo_viewable_profile_ids(
    db: AsyncSession, viewer_user: User | None, profiles: Iterable[Profile]
) -> set[int]:
    """Ids of the given profiles whose photos (and horoscope charts) the viewer may see.

    Admins and moderators see all. Anyone else sees their own, and otherwise
    only profiles they may open at all — the get_profile_for_viewer rules:
    legal marriage age (theirs and the viewer's), visibility, no block in
    either direction — that also either do not blur photos or are linked to
    the viewer's profile by an ACCEPTED interest (either direction). So no
    caller can hand out a photo URL that the profile or photos endpoint would
    refuse. At most three queries for the whole batch (viewer's age, blocks,
    interests).
    """
    profiles = list(profiles)
    if is_reviewer(viewer_user):
        return {p.id for p in profiles}

    viewer_id = viewer_user.id if viewer_user is not None else None
    own = {p.id for p in profiles if viewer_id is not None and p.user_id == viewer_id}
    # An under-age viewer sees only their own, even through an accepted interest
    if len(own) < len(profiles) and await is_underage_viewer(db, viewer_user):
        return own
    others = [
        p for p in profiles
        if p.id not in own
        and meets_minimum_age(p.date_of_birth, p.gender)
        and check_visibility(p, viewer_user)
    ]
    if others and viewer_id is not None:
        from app.services.safety_service import get_blocked_user_ids
        blocked = await get_blocked_user_ids(db, viewer_id)
        others = [p for p in others if p.user_id not in blocked]

    allowed = own | {p.id for p in others if not p.photo_blur_until_mutual}
    pending = {p.id for p in others if p.photo_blur_until_mutual}
    if not pending or viewer_id is None:
        return allowed

    # Interests link PROFILE ids; resolve the viewer's in SQL (they may have none)
    viewer_profile_id = select(Profile.id).where(Profile.user_id == viewer_id).scalar_subquery()
    rows = await db.execute(
        select(Interest.sender_id, Interest.receiver_id).where(
            Interest.status == InterestStatus.accepted.value,
            or_(
                and_(Interest.sender_id == viewer_profile_id, Interest.receiver_id.in_(pending)),
                and_(Interest.receiver_id == viewer_profile_id, Interest.sender_id.in_(pending)),
            ),
        )
    )
    for sender_id, receiver_id in rows.all():
        allowed |= {sender_id, receiver_id} & pending
    return allowed


async def can_view_photos(db: AsyncSession, viewer_user: User | None, profile: Profile) -> bool:
    """Server-side photo blur: may the viewer see this profile's photos and charts?"""
    return profile.id in await photo_viewable_profile_ids(db, viewer_user, [profile])


def photo_url(storage_key: str) -> str:
    """Public path of a stored photo (served by the /uploads static mount)."""
    if storage_key.startswith(("http://", "https://")):
        return storage_key
    return "/" + storage_key.lstrip("/")


async def get_display_photo_urls(db: AsyncSession, profile_ids: Iterable[int]) -> dict[int, str]:
    """Map profile id → URL of its display photo: the primary approved photo,
    else the most recent approved one. Profiles without one are absent.
    Callers must pass only profiles the viewer may see photos of."""
    profile_ids = set(profile_ids)
    if not profile_ids:
        return {}
    result = await db.execute(
        select(ProfilePhoto.profile_id, ProfilePhoto.storage_key)
        .where(ProfilePhoto.profile_id.in_(profile_ids), ProfilePhoto.is_approved.is_(True))
        # coalesce: legacy NULL is_primary must not sort first (Postgres puts NULLs first on DESC)
        .order_by(
            func.coalesce(ProfilePhoto.is_primary, False).desc(),
            ProfilePhoto.created_at.desc(),
            ProfilePhoto.id.desc(),
        )
    )
    urls: dict[int, str] = {}
    for profile_id, storage_key in result.all():
        urls.setdefault(profile_id, photo_url(storage_key))  # first row wins
    return urls


async def photo_fields_for_viewer(
    db: AsyncSession, viewer_user: User | None, profiles: Iterable[Profile]
) -> dict[int, dict]:
    """profile id -> the ProfilePublicOut photo fields for this viewer:
    profile_photo ({"url": ...} of the display photo, or None) and
    photo_locked (True when the member has approved photos this viewer may
    not see yet; a member with no approved photo is never locked, matching
    what /profiles/{id}/photos reports). For list endpoints; at most five
    queries whatever the number of profiles."""
    profiles = list(profiles)
    viewable = await photo_viewable_profile_ids(db, viewer_user, profiles)
    urls = await get_display_photo_urls(db, viewable)
    hidden = {p.id for p in profiles} - viewable
    locked = set()
    if hidden:
        locked = set((await db.scalars(
            select(ProfilePhoto.profile_id).distinct().where(
                ProfilePhoto.profile_id.in_(hidden), ProfilePhoto.is_approved.is_(True)
            )
        )).all())
    return {
        p.id: {
            "profile_photo": {"url": urls[p.id]} if p.id in urls else None,
            "photo_locked": p.id in locked,
        }
        for p in profiles
    }
