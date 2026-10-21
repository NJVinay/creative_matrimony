"""
Matching Service.
Trace: @context_documents/MVP_BACKLOG.md Epic F, G
"""

from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, not_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile, Gender
from app.models.match import Preference
from app.models.communication import Interest
from app.models.horoscope import Horoscope, Rasi, Star
from app.models.safety import UserBlock
from app.services.profile_service import legal_age_condition, meets_minimum_age

# Classical ordering used for porutham-style counting
STAR_ORDER = list(Star)   # 27 nakshatras, Ashwini → Revati
RASI_ORDER = list(Rasi)   # 12 rasis, Mesha → Meena

# Weight of the horoscope component in the blended score (Epic F2)
HOROSCOPE_WEIGHT = 0.2


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
    def horoscope_compatibility(
        seeker: Optional[Horoscope], candidate: Optional[Horoscope]
    ) -> Tuple[Optional[int], List[str]]:
        """
        Simplified porutham-style compatibility (0-100) from star, rasi, and dosham.
        Only criteria present on BOTH sides are evaluated; the result is scaled to
        the evaluated weight. Returns (None, []) when nothing can be evaluated.
        Trace: @context_documents/MVP_BACKLOG.md Epic F2
        """
        if not seeker or not candidate:
            return None, []

        earned, possible = 0, 0
        reasons: List[str] = []

        # Dina porutham (40): count from seeker's star to candidate's star
        if seeker.star and candidate.star:
            possible += 40
            count = ((STAR_ORDER.index(candidate.star) - STAR_ORDER.index(seeker.star)) % 27) + 1
            if count % 9 in (0, 2, 4, 6, 8):
                earned += 40
                reasons.append("Favourable star (dina) compatibility")

        # Rasi placement (40): avoids 2/12, 5/9 and 6/8 dosha positions
        if seeker.rasi and candidate.rasi:
            possible += 40
            dist = ((RASI_ORDER.index(candidate.rasi) - RASI_ORDER.index(seeker.rasi)) % 12) + 1
            if dist in (1, 3, 4, 7, 10, 11):
                earned += 40
                reasons.append("Favourable rasi placement")

        # Dosham alignment (20): matched dosham status is traditionally preferred
        if seeker.dosham is not None and candidate.dosham is not None:
            possible += 20
            if bool(seeker.dosham) == bool(candidate.dosham):
                earned += 20
                if seeker.dosham:
                    reasons.append("Matching dosham status")

        if possible == 0:
            return None, []
        return round(earned * 100 / possible), reasons

    @staticmethod
    def calculate_score(
        candidate: Profile,
        pref: Preference,
        seeker_horoscope: Optional[Horoscope] = None,
    ) -> Tuple[int, List[str], int]:
        """
        Scoring Algorithm (0-100) with confidence metric.
        Base components:
        - Age (25 pts): Within range.
        - Height (15 pts): Within range.
        - Marital Status (20 pts): Matches.
        - Community (20 pts): Matches.
        - Location (20 pts): State matches.
        Horoscope (Epic F2): when both sides have data, the horoscope
        compatibility is blended in at HOROSCOPE_WEIGHT and confidence rises.
        Confidence = share of the 6 criteria that could actually be evaluated.
        Returns (score, reasons, confidence).
        """
        score = 0
        reasons = []
        evaluated = 4  # age, marital status, community, location are always evaluable

        # Age
        if pref.min_age <= candidate.age <= pref.max_age:
            score += 25
            reasons.append("Matches your age preference")

        # Height (if set)
        if pref.min_height and pref.max_height and candidate.height_cm:
            if pref.min_height <= candidate.height_cm <= pref.max_height:
                score += 15
                reasons.append("Matches your height preference")
            evaluated += 1
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

        # Horoscope contribution (Epic F2)
        horo_score, horo_reasons = MatchingService.horoscope_compatibility(
            seeker_horoscope, getattr(candidate, "horoscope", None)
        )
        if horo_score is not None:
            score = round(score * (1 - HOROSCOPE_WEIGHT) + horo_score * HOROSCOPE_WEIGHT)
            reasons.extend(horo_reasons)
            reasons.append(f"Horoscope compatibility {horo_score}%")
            evaluated += 1

        confidence = round(evaluated * 100 / 6)
        return score, reasons, confidence

    @staticmethod
    async def get_recommendations(
        db: AsyncSession,
        user_profile_id: int,
        limit: int = 20
    ) -> List[Tuple[Profile, int, List[str], int]]:
        """Returns list of (Profile, score, reasons, confidence) tuples sorted by score."""

        # 1. Get User Preference, Profile, and Horoscope (for Epic F2 contribution)
        result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.preference), selectinload(Profile.horoscope))
            .where(Profile.id == user_profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return []
        # Legacy under-age profiles (created before the DOB check) get no matches
        if not meets_minimum_age(profile.date_of_birth, profile.gender):
            return []

        pref = await MatchingService.get_or_create_preference(db, user_profile_id)

        # 2. Get Exclusions (Already interacted)
        # Sent or Received interests
        sent_stmt = select(Interest.receiver_id).where(Interest.sender_id == user_profile_id)
        received_stmt = select(Interest.sender_id).where(Interest.receiver_id == user_profile_id)

        sent_ids = (await db.execute(sent_stmt)).scalars().all()
        received_ids = (await db.execute(received_stmt)).scalars().all()
        excluded_ids = set(sent_ids) | set(received_ids) | {user_profile_id}

        # 2b. Exclude blocked users, in either direction (panic block — Safety)
        blocked_stmt = select(UserBlock.blocked_user_id).where(UserBlock.blocker_user_id == profile.user_id)
        blockers_stmt = select(UserBlock.blocker_user_id).where(UserBlock.blocked_user_id == profile.user_id)
        blocked_user_ids = set((await db.execute(blocked_stmt)).scalars().all()) | set(
            (await db.execute(blockers_stmt)).scalars().all()
        )

        # 3. Base Query for Candidates
        # Filter by Opposite Gender (for MVP heteronormative default, or strict if specified)
        target_gender = Gender.female if profile.gender == Gender.male else Gender.male
        if profile.gender == Gender.other:
            target_gender = None # dynamic?

        query = select(Profile).options(
            selectinload(Profile.horoscope),
            selectinload(Profile.user),  # needed for is_verified in the public view
        ).where(
            Profile.id.notin_(excluded_ids),
            Profile.visibility != "hidden",
            Profile.is_active == True,
            # Hard filter, independent of preferences: age preferences only
            # add score points, so they can never be what keeps minors out.
            legal_age_condition(),
        )
        if blocked_user_ids:
            query = query.where(Profile.user_id.notin_(blocked_user_ids))

        if target_gender:
            query = query.where(Profile.gender == target_gender)

        # 4. Fetch Batch (Optimize: Filter roughly by DB first? For now fetch all valid and score in python for "best" accuracy on small dataset)
        # Limit DB fetch to e.g. 100 recent active profiles to score
        query = query.limit(100)

        candidates = (await db.execute(query)).scalars().all()

        # 5. Score & Sort
        scored_candidates = []
        for cand in candidates:
            score, reasons, confidence = MatchingService.calculate_score(cand, pref, profile.horoscope)
            if score > 0: # Only return if some match
                scored_candidates.append((cand, score, reasons, confidence))

        # Sort desc by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates[:limit]
