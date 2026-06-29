"""
Taxonomy API — public listing + admin CRUD + user suggestions.
Trace: @context_documents/DATA_TAXONOMY_SPEC.md, @context_documents/MVP_BACKLOG.md Epic C
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models.taxonomy import (
    RegionGroup, LanguageGroup, Religion, Community, SubCaste,
)
from app.models.user import User, UserRole
from app.schemas.taxonomy import (
    TaxonomyItemOut, RegionGroupOut, LanguageGroupOut,
    CommunityOut, SubCasteOut,
    TaxonomyCreateIn, CommunityCreateIn, SubCasteCreateIn,
    TaxonomySuggestIn, TaxonomySuggestOut,
    TaxonomySuggestionOut, TaxonomyResolveIn,
)
from app.services.taxonomy_service import (
    list_religions, list_communities, list_subcastes,
    list_region_groups, list_language_groups,
    submit_unknown_value,
)

router = APIRouter(prefix="/taxonomy", tags=["Taxonomy"])


# ── Public endpoints ─────────────────────────────────────

@router.get("/religions", response_model=list[TaxonomyItemOut])
async def get_religions(db: Annotated[AsyncSession, Depends(get_db)]):
    return await list_religions(db)


@router.get("/communities", response_model=list[CommunityOut])
async def get_communities(
    db: Annotated[AsyncSession, Depends(get_db)],
    religion_id: int | None = None,
    language_group_id: int | None = None,
):
    return await list_communities(db, religion_id, language_group_id)


@router.get("/subcastes", response_model=list[SubCasteOut])
async def get_subcastes(
    community_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_subcastes(db, community_id)


@router.get("/regions", response_model=list[RegionGroupOut])
async def get_regions(db: Annotated[AsyncSession, Depends(get_db)]):
    return await list_region_groups(db)


@router.get("/language-groups", response_model=list[LanguageGroupOut])
async def get_language_groups(db: Annotated[AsyncSession, Depends(get_db)]):
    return await list_language_groups(db)


# ── User suggestion (unknown taxonomy value → moderation queue) ──

@router.post("/suggest", response_model=TaxonomySuggestOut, status_code=status.HTTP_201_CREATED)
async def suggest_taxonomy_value(
    body: TaxonomySuggestIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Submit an unknown taxonomy value for moderator review."""
    entry = await submit_unknown_value(db, user.id, body.value, body.field_name)
    return TaxonomySuggestOut(id=entry.id)


# ── Admin CRUD ───────────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/taxonomy",
    tags=["Admin – Taxonomy"],
    dependencies=[Depends(require_roles(UserRole.admin))],
)


@admin_router.post("/religions", response_model=TaxonomyItemOut, status_code=201)
async def create_religion(
    body: TaxonomyCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    religion = Religion(
        canonical_id=body.canonical_id,
        name_en=body.name_en,
        name_te=body.name_te,
    )
    db.add(religion)
    await db.flush()
    await db.refresh(religion)
    return religion


@admin_router.post("/communities", response_model=CommunityOut, status_code=201)
async def create_community(
    body: CommunityCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    community = Community(
        canonical_id=body.canonical_id,
        name_en=body.name_en,
        name_te=body.name_te,
        religion_id=body.religion_id,
        language_group_id=body.language_group_id,
    )
    db.add(community)
    await db.flush()
    await db.refresh(community)
    return community


@admin_router.post("/subcastes", response_model=SubCasteOut, status_code=201)
async def create_subcaste(
    body: SubCasteCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subcaste = SubCaste(
        canonical_id=body.canonical_id,
        name_en=body.name_en,
        name_te=body.name_te,
        community_id=body.community_id,
    )
    db.add(subcaste)
    await db.flush()
    await db.refresh(subcaste)
    return subcaste

from sqlalchemy import select
from app.models.taxonomy import TaxonomyModerationQueue, TaxonomySynonym

@admin_router.get("/suggestions", response_model=list[TaxonomySuggestionOut])
async def list_suggestions(db: Annotated[AsyncSession, Depends(get_db)]):
    """List pending taxonomy suggestions."""
    result = await db.execute(
        select(TaxonomyModerationQueue)
        .where(TaxonomyModerationQueue.status == "pending")
        .order_by(TaxonomyModerationQueue.created_at.desc())
    )
    items = result.scalars().all()
    return [
        TaxonomySuggestionOut(
            id=item.id,
            user_id=item.user_id,
            user_submitted_value=item.user_submitted_value,
            field_name=item.field_name,
            status=item.status.value if hasattr(item.status, 'value') else item.status,
            created_at=item.created_at.isoformat() if item.created_at else ""
        ) for item in items
    ]

@admin_router.post("/suggestions/{suggestion_id}/resolve")
async def resolve_suggestion(
    suggestion_id: int,
    body: TaxonomyResolveIn,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Resolve a taxonomy suggestion by mapping it to a canonical ID or rejecting it."""
    suggestion = await db.get(TaxonomyModerationQueue, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
        
    if body.action == "reject":
        suggestion.status = "rejected"
    elif body.action == "approve":
        if not body.target_id:
            raise HTTPException(status_code=400, detail="target_id is required for approval")
            
        suggestion.status = "approved"
        
        # Create a synonym mapping
        synonym = TaxonomySynonym(
            term=suggestion.user_submitted_value,
            target_type=suggestion.field_name,
            target_id=body.target_id,
            is_approved=True,
            created_by=suggestion.user_id,
        )
        db.add(synonym)
        
    await db.commit()
    return {"status": suggestion.status}
