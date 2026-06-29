"""
Search Service — Advanced filtering logic.
Trace: @context_documents/MVP_BACKLOG.md Epic E
"""

from datetime import date
from typing import Optional, List

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import Profile, Gender, MaritalStatus, Visibility
from app.models.user import User


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
    filters: SearchFilters,
    current_user_id: Optional[int] = None,
) -> list:
    """Shared WHERE-clause builder used by both search_profiles and count_profiles."""
    today = date.today()
    max_dob = today.replace(year=today.year - filters.min_age)
    min_dob = today.replace(year=today.year - filters.max_age - 1)

    conditions = [
        Profile.is_active.is_(True),
        Profile.visibility != Visibility.hidden,
        Profile.date_of_birth <= max_dob,
        Profile.date_of_birth > min_dob,
    ]

    if current_user_id:
        conditions.append(Profile.user_id != current_user_id)

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
    current_user_id: Optional[int] = None
) -> List[Profile]:
    """
    Execute search with dynamic filters.
    Enforces visibility rules (hidden profiles are excluded).
    Verified-only logic is handled at the API layer (depends on viewer context).
    """
    conditions = await _build_filter_conditions(filters, current_user_id)

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
    current_user_id: Optional[int] = None
) -> int:
    """Count total matches for pagination (same WHERE clause as search_profiles)."""
    conditions = await _build_filter_conditions(filters, current_user_id)
    stmt = select(func.count(Profile.id)).where(*conditions)
    result = await db.execute(stmt)
    return int(result.scalar() or 0) 
