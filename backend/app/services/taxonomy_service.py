"""
Taxonomy service — query, synonym resolution, moderation queue.
Trace: @context_documents/DATA_TAXONOMY_SPEC.md, @context_documents/MVP_BACKLOG.md Epic C
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taxonomy import (
    RegionGroup, LanguageGroup, Religion, Community, SubCaste,
    TaxonomySynonym, TaxonomyModerationQueue, ModerationStatus,
)


async def list_religions(db: AsyncSession) -> list[Religion]:
    result = await db.execute(select(Religion).order_by(Religion.name_en))
    return list(result.scalars().all())


async def list_communities(
    db: AsyncSession,
    religion_id: int | None = None,
    language_group_id: int | None = None,
) -> list[Community]:
    query = select(Community)
    if religion_id:
        query = query.where(Community.religion_id == religion_id)
    if language_group_id:
        query = query.where(Community.language_group_id == language_group_id)
    result = await db.execute(query.order_by(Community.name_en))
    return list(result.scalars().all())


async def list_subcastes(db: AsyncSession, community_id: int) -> list[SubCaste]:
    result = await db.execute(
        select(SubCaste)
        .where(SubCaste.community_id == community_id)
        .order_by(SubCaste.name_en)
    )
    return list(result.scalars().all())


async def list_region_groups(db: AsyncSession) -> list[RegionGroup]:
    result = await db.execute(select(RegionGroup).order_by(RegionGroup.sort_order))
    return list(result.scalars().all())


async def list_language_groups(db: AsyncSession) -> list[LanguageGroup]:
    result = await db.execute(select(LanguageGroup).order_by(LanguageGroup.name_en))
    return list(result.scalars().all())


async def resolve_synonym(db: AsyncSession, term: str, target_type: str) -> int | None:
    """Resolve a synonym to its canonical taxonomy ID."""
    result = await db.execute(
        select(TaxonomySynonym)
        .where(
            TaxonomySynonym.term.ilike(term),
            TaxonomySynonym.target_type == target_type,
            TaxonomySynonym.is_approved.is_(True),
        )
        .limit(1)
    )
    synonym = result.scalar_one_or_none()
    return synonym.target_id if synonym else None


async def submit_unknown_value(
    db: AsyncSession,
    user_id: int,
    value: str,
    field_name: str,
) -> TaxonomyModerationQueue:
    """Submit an unknown taxonomy value for moderator review."""
    entry = TaxonomyModerationQueue(
        user_submitted_value=value,
        field_name=field_name,
        user_id=user_id,
        status=ModerationStatus.pending,
    )
    db.add(entry)
    await db.flush()
    return entry
