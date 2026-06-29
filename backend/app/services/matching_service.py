"""
Matching Service.
Trace: @context_documents/MVP_BACKLOG.md Epic F
"""

from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, not_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile, Gender
from app.models.match import Preference
from app.models.communication import Interest

class MatchingService:
    @staticmethod
    async def get_or_create_preference(db: AsyncSession, profile_id: int) -> Preference:
        result = await db.execute(select(Preference).where(Preference.profile_id == profile_id))
        pref = result.scalar_one_or_none()
        if not pref:
            pref = Preference(profile_id=profile_id)
            db.add(pref)
            await db.commit()
            await db.refresh(pref)
        return pref

    @staticmethod
    async def update_preference(db: AsyncSession, profile_id: int, data: dict) -> Preference:
        pref = await MatchingService.get_or_create_preference(db, profile_id)
        for key, value in data.items():
            if hasattr(pref, key):
                setattr(pref, key, value)
        await db.commit()
        await db.refresh(pref)
        return pref

    @staticmethod
    def calculate_score(candidate: Profile, pref: Preference) -> Tuple[int, List[str]]:
        """
        Scoring Algorithm (0-100).
        - Age (25 pts): Within range.
        - Height (15 pts): Within range.
        - Marital Status (20 pts): Matches.
        - Community (20 pts): Matches.
        - Location (20 pts): State matches.
        """
        score = 0
        reasons = []
        
        # Age
        if pref.min_age <= candidate.age <= pref.max_age:
            score += 25
            reasons.append("Matches your age preference")
            
        # Height (if set)
        if pref.min_height and pref.max_height and candidate.height_cm:
            if pref.min_height <= candidate.height_cm <= pref.max_height:
                score += 15
                reasons.append("Matches your height preference")
        elif not pref.min_height: # If no preference, give partial points
            score += 10
            
        # Marital Status
        if not pref.marital_status or (candidate.marital_status in pref.marital_status):
            score += 20
            reasons.append("Matches preferred marital status")
            
        # Community
        if not pref.community_id or (candidate.community_id in pref.community_id):
            score += 20
            reasons.append("Same community preference")
            
        # Location (State)
        if not pref.state or (candidate.state == pref.state):
            score += 20
            reasons.append("In your preferred location")
            
        return score, reasons

    @staticmethod
    async def get_recommendations(
        db: AsyncSession, 
        user_profile_id: int, 
        limit: int = 20
    ) -> List[Tuple[Profile, int, List[str]]]:
        """Returns list of (Profile, score, reasons) tuples sorted by score."""
        
        # 1. Get User Preference & Profile
        result = await db.execute(
            select(Profile).options(selectinload(Profile.preference)).where(Profile.id == user_profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return []

        pref = await MatchingService.get_or_create_preference(db, user_profile_id)

        # 2. Get Exclusions (Already interacted)
        # Sent or Received interests
        sent_stmt = select(Interest.receiver_id).where(Interest.sender_id == user_profile_id)
        received_stmt = select(Interest.sender_id).where(Interest.receiver_id == user_profile_id)
        
        sent_ids = (await db.execute(sent_stmt)).scalars().all()
        received_ids = (await db.execute(received_stmt)).scalars().all()
        excluded_ids = set(sent_ids) | set(received_ids) | {user_profile_id}

        # 3. Base Query for Candidates
        # Filter by Opposite Gender (for MVP heteronormative default, or strict if specified)
        # Actually Profile has 'gender', let's just assume opposite for MVP or check logic
        target_gender = Gender.female if profile.gender == Gender.male else Gender.male
        if profile.gender == Gender.other:
            target_gender = None # dynamic?

        query = select(Profile).where(
            Profile.id.notin_(excluded_ids),
            Profile.visibility != "hidden",
            Profile.is_active == True
        )
        
        if target_gender:
            query = query.where(Profile.gender == target_gender)

        # 4. Fetch Batch (Optimize: Filter roughly by DB first? For now fetch all valid and score in python for "best" accuracy on small dataset)
        # Limit DB fetch to e.g. 100 recent active profiles to score
        query = query.limit(100)
        
        candidates = (await db.execute(query)).scalars().all()
        
        # 5. Score & Sort
        scored_candidates = []
        for cand in candidates:
            score, reasons = MatchingService.calculate_score(cand, pref)
            if score > 0: # Only return if some match
                scored_candidates.append((cand, score, reasons))
        
        # Sort desc by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [(c, s, r) for c, s, r in scored_candidates[:limit]]
