"""
Match API.
Trace: @context_documents/MVP_BACKLOG.md Epic F
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.matching_service import MatchingService
from app.schemas.match import PreferenceOut, PreferenceUpdate, MatchRecommendation
from app.schemas.profile import ProfilePublicOut

router = APIRouter(prefix="/matches", tags=["Matching"])

@router.get("/recommendations", response_model=List[MatchRecommendation])
async def get_recommendations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20
):
    """
    Get sorted list of recommended profiles based on preferences.
    Scores candidates 0-100.
    """
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required for matching")
        
    # Get matches from service
    matches = await MatchingService.get_recommendations(db, user.profile.id, limit)
    
    # Convert to schema
    return [
        MatchRecommendation(
            profile=ProfilePublicOut.model_validate(p),
            score=s,
            reasons=r
        ) for p, s, r in matches
    ]

@router.get("/preferences", response_model=PreferenceOut)
async def get_my_preferences(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    return await MatchingService.get_or_create_preference(db, user.profile.id)

@router.put("/preferences", response_model=PreferenceOut)
async def update_my_preferences(
    preference: PreferenceUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not user.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    
    return await MatchingService.update_preference(
        db, 
        user.profile.id, 
        preference.model_dump(exclude_unset=True)
    )
