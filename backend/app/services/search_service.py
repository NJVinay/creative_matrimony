"""
Search Service — Advanced filtering logic.
Trace: @context_documents/MVP_BACKLOG.md Epic E
"""

from datetime import date
from typing import Optional, List

from sqlalchemy import select, and_, or_, desc, func, false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import Profile, Gender, MaritalStatus
from app.models.user import User
from app.services.profile_service import (
    is_underage_viewer, legal_age_condition, visibility_condition, years_ago,
)
from app.services.safety_service import get_blocked_user_ids


class SearchFilters:
    """Filter criteria for profile search."""
    def __init__(
        self,
        min_age: int = 18,
        max_age: int = 60,
        gender: Optional[str] = None,
        marital_status: Optional[List[str]] = None,
        religion_id: Optional[int] = None,
        community_id: Optional[List[int]] = None,
        city_village: Optional[str] = None,
        state: Optional[str] = None,
        education_level: Optional[str] = None,
        occupation_category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ):
        self.min_age = min_age
        self.max_age = max_age
        self.gender = gender
        self.marital_status = marital_status
        self.religion_id = religion_id
        self.community_id = community_id
        self.city_village = city_village
        self.state = state
        self.education_level = education_level
        self.occupation_category = occupation_category
        self.limit = limit
        self.offset = offset


async def _build_filter_conditions(
    db: AsyncSession,
    filters: SearchFilters,
    viewer: Optional[User] = None,
) -> list:
    """Shared WHERE-clause builder used by both search_profiles and count_profiles.
    Every rule that depends on the viewer is applied here, in SQL, so the
    total and the pages always agree."""
    today = date.today()
    max_dob = years_ago(filters.min_age, today)
    min_dob = years_ago(filters.max_age + 1, today)

    conditions = [
        Profile.is_active.is_(True),
        # Same rule as the profile page: never hidden, verified-only for verified viewers
        visibility_condition(viewer),
        Profile.date_of_birth <= max_dob,
        Profile.date_of_birth > min_dob,
        legal_age_condition(today),  # never list anyone under the legal marriage age
    ]

    if viewer is not None:
        # A viewer below the legal marriage age (legacy row) is shown no one
        if await is_underage_viewer(db, viewer):
            return [false()]
        conditions.append(Profile.user_id != viewer.id)
        # Panic block: blocked users never see each other, in either direction
        blocked = await get_blocked_user_ids(db, viewer.id)
        if blocked:
            conditions.append(Profile.user_id.notin_(blocked))

    if filters.gender:
        conditions.append(Profile.gender == Gender(filters.gender))

    if filters.marital_status:
        statuses = [MaritalStatus(s) for s in filters.marital_status]
        conditions.append(Profile.marital_status.in_(statuses))

    if filters.religion_id:
        conditions.append(Profile.religion_id == filters.religion_id)

    if filters.community_id:
        conditions.append(Profile.community_id.in_(filters.community_id))

    if filters.state:
        conditions.append(Profile.state.ilike(f"%{filters.state}%"))

    if filters.city_village:
        conditions.append(Profile.city_village.ilike(f"%{filters.city_village}%"))

    if filters.education_level:
        conditions.append(Profile.education_level.ilike(f"%{filters.education_level}%"))

    if filters.occupation_category:
        conditions.append(Profile.occupation_category.ilike(f"%{filters.occupation_category}%"))

    return conditions


async def search_profiles(
    db: AsyncSession,
    filters: SearchFilters,
    viewer: Optional[User] = None
) -> List[Profile]:
    """
    Execute search with dynamic filters, as seen by `viewer`: visibility
    (hidden, verified-only), legal age, blocks and the viewer's own profile
    are all applied in SQL.
    """
    conditions = await _build_filter_conditions(db, filters, viewer)

    query = (
        select(Profile)
        .where(*conditions)
        .order_by(desc(Profile.updated_at))
        .offset(filters.offset)
        .limit(filters.limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def count_profiles(
    db: AsyncSession,
    filters: SearchFilters,
    viewer: Optional[User] = None
) -> int:
    """Count total matches for pagination (same WHERE clause as search_profiles)."""
    conditions = await _build_filter_conditions(db, filters, viewer)
    stmt = select(func.count(Profile.id)).where(*conditions)
    result = await db.execute(stmt)
    return int(result.scalar() or 0) 
