"""
Search API — Find matches.
Trace: @context_documents/MVP_BACKLOG.md Epic E
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.schemas.profile import ProfilePublicOut
from app.services.search_service import search_profiles, count_profiles, SearchFilters
from app.services.profile_service import to_public_view, photo_fields_for_viewer

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search_matches(
    body: SearchRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Search profiles.
    Requires auth.
    Privacy rules (hidden, verified-only, hide-from-search, legal age, blocks)
    are applied in the query itself, so `total` counts exactly the profiles the
    pages can show.
    Loads profiles + owners in a single batched query (no N+1).
    """
    filters = SearchFilters(
        min_age=body.min_age,
        max_age=body.max_age,
        gender=body.gender,
        marital_status=body.marital_status,
        religion_id=body.religion_id,
        community_id=body.community_id,
        city_village=body.city_village,
        state=body.state,
        education_level=body.education_level,
        occupation_category=body.occupation_category,
        limit=body.limit,
        offset=(body.page - 1) * body.limit,
    )

    visible_profiles = await search_profiles(db, filters, viewer=user)

    # Fetch owners in a single query (no N+1)
    owners_by_id: dict[int, User] = {}
    if visible_profiles:
        owner_ids = {p.user_id for p in visible_profiles}
        owners_stmt = select(User).where(User.id.in_(owner_ids))
        owners_result = await db.execute(owners_stmt)
        for u in owners_result.scalars().all():
            owners_by_id[u.id] = u

    # Display photos with the same batched access check as recommendations,
    # so a card's photo/lock state matches what /profile/{id} would show
    photos = await photo_fields_for_viewer(db, user, visible_profiles)

    visible_results = [
        ProfilePublicOut(**to_public_view(p, owners_by_id.get(p.user_id)), **photos[p.id])
        for p in visible_profiles
    ]

    total = await count_profiles(db, filters, viewer=user)

    return SearchResponse(
        results=visible_results,
        page=body.page,
        limit=body.limit,
        total=total,
    )
