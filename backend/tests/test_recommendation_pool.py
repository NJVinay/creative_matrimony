"""Recommendations score the right candidates: the database ranks every
eligible member by preference fit before the MATCH_CANDIDATE_POOL cut, the
same data always gives the same list, and members who chose "Hide completely
from Search" never appear in the daily matches (app or weekly digest)."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from tests.conftest import make_client, create_profile
from app.config import settings
from app.database import async_session
from app.models.match import Preference
from app.models.profile import Profile, Gender, MaritalStatus, ProfileMode, Visibility
from app.models.taxonomy import Community, LanguageGroup, Religion
from app.models.user import User
from app.services import digest_service
from app.services.matching_service import MatchingService
from app.services.profile_service import years_ago


async def _communities(tag: str, count: int) -> list[int]:
    """Fresh community ids, so no other test's member shares them."""
    async with async_session() as session:
        religion = Religion(canonical_id=f"{tag}_religion", name_en=f"{tag} religion")
        language = LanguageGroup(canonical_id=f"{tag}_language", name_en=f"{tag} language")
        session.add_all([religion, language])
        await session.flush()
        communities = [
            Community(canonical_id=f"{tag}_community_{i}", name_en=f"{tag} community {i}",
                      religion_id=religion.id, language_group_id=language.id)
            for i in range(count)
        ]
        session.add_all(communities)
        await session.commit()
        return [c.id for c in communities]


async def _add_member(phone: str, name: str, gender: Gender, age: int, **fields) -> int:
    """An active, public member (and its user), inserted directly; returns the profile id."""
    async with async_session() as session:
        user = User(phone=phone)
        session.add(user)
        await session.flush()
        profile = Profile(
            user_id=user.id, profile_mode=ProfileMode.self_managed, display_name=name,
            gender=gender, date_of_birth=years_ago(age), city_village="Poolpuram",
            completion_pct=60.0, is_active=True, visibility=Visibility.public, **fields,
        )
        session.add(profile)
        await session.commit()
        return profile.id


async def _recommendations(seeker_id: int, limit: int = 500) -> list[tuple[int, int]]:
    """(profile id, score) of the seeker's recommendations, in order."""
    async with async_session() as session:
        recs = await MatchingService.get_recommendations(session, seeker_id, limit)
    return [(p.id, score) for p, score, _reasons, _confidence in recs]


async def _scenario(phone_base: str) -> tuple[int, list[int], list[int]]:
    """A seeker, 3 perfect matches and 4 poor ones, all in a state and community
    no other test uses. Two poor matches are inserted before the perfect ones
    (insertion order alone would pick them) and two after (recency alone would).
    Returns (seeker, poor, good)."""
    tag = f"pool{uuid.uuid4().hex[:8]}"
    state = f"Poolpradesh {tag}"
    good_community, other_community = await _communities(tag, 2)

    seeker = await _add_member(f"{phone_base}0", "Pool Seeker", Gender.male, 31, state=state)
    async with async_session() as session:
        await MatchingService.update_preference(session, seeker, {
            "min_age": 25, "max_age": 32, "min_height": 150, "max_height": 170,
            "marital_status": ["never_married"], "community_id": [good_community], "state": state,
        })

    async def poor_match(i: int) -> int:
        # Right age and state only: 45 points
        return await _add_member(f"{phone_base}{i}", f"Poor Match {i}", Gender.female, 28,
                                 height_cm=185, marital_status=MaritalStatus.divorced,
                                 community_id=other_community, state=state)

    poor = [await poor_match(i) for i in (1, 2)]
    # Every preference met: 100 points
    good = [
        await _add_member(f"{phone_base}{i}", f"Good Match {i}", Gender.female, 27,
                          height_cm=160, marital_status=MaritalStatus.never_married,
                          community_id=good_community, state=state)
        for i in (3, 4, 5)
    ]
    poor += [await poor_match(i) for i in (6, 7)]
    return seeker, poor, good


@pytest.mark.asyncio
async def test_small_pool_still_scores_the_best_matches(monkeypatch):
    seeker, poor, good = await _scenario("+91973000510")

    # Pool smaller than the eligible set: the cut must keep the best fits.
    # Nobody else in the DB lives in this state or community, so the 3
    # perfect matches are the 3 best candidates there are.
    monkeypatch.setattr(settings, "MATCH_CANDIDATE_POOL", 3)
    recs = await _recommendations(seeker)
    assert {pid for pid, _ in recs} == set(good) and len(recs) == 3
    assert all(score == 100 for _, score in recs)

    # With room for everyone the poor matches are eligible and scored too:
    # only the pool cut left them out above
    monkeypatch.setattr(settings, "MATCH_CANDIDATE_POOL", 300)
    mine = [(pid, score) for pid, score in await _recommendations(seeker) if pid in poor + good]
    assert {pid for pid, _ in mine[:3]} == set(good)
    assert {pid for pid, _ in mine[3:]} == set(poor)
    assert all(score == 45 for _, score in mine[3:])


@pytest.mark.asyncio
async def test_recommendations_are_deterministic_and_ties_go_to_recent(monkeypatch):
    seeker, poor, good = await _scenario("+91973000520")
    monkeypatch.setattr(settings, "MATCH_CANDIDATE_POOL", 3)

    first = await _recommendations(seeker)
    for _ in range(3):
        assert await _recommendations(seeker) == first
    # Equal scores: newest first (all inserted in order, so by id descending)
    assert [pid for pid, _ in first] == sorted(good, reverse=True)

    # The most recently updated profile wins a tie, then the newest
    async with async_session() as session:
        await session.execute(
            update(Profile).where(Profile.id == good[0])
            .values(updated_at=datetime.now() + timedelta(days=1))
        )
        await session.commit()
    expected = [good[0]] + sorted(good[1:], reverse=True)
    for _ in range(3):
        assert [pid for pid, _ in await _recommendations(seeker)] == expected

    monkeypatch.setattr(settings, "MATCH_CANDIDATE_POOL", 300)
    full = await _recommendations(seeker)
    assert full == await _recommendations(seeker)
    assert [pid for pid, _ in full if pid in poor + good] == expected + sorted(poor, reverse=True)


@pytest.mark.asyncio
async def test_hide_from_search_member_is_never_recommended(monkeypatch):
    tag = f"pool{uuid.uuid4().hex[:8]}"
    state = f"Hidepradesh {tag}"
    (community,) = await _communities(tag, 1)
    seeker = await make_client("+919730005300")
    try:
        p_seeker = await create_profile(seeker, display_name="Hide Seeker", gender="male",
                                        date_of_birth="1995-01-15", state=state)
        resp = await seeker.put("/api/matches/preferences", json={
            "min_age": 25, "max_age": 35, "min_height": 150, "max_height": 170,
            "marital_status": ["never_married"], "community_id": [community], "state": state,
        })
        assert resp.status_code == 200, resp.text

        perfect = dict(height_cm=160, marital_status=MaritalStatus.never_married,
                       community_id=community, state=state)
        visible = [await _add_member(f"+91973000530{1 + i}", f"Visible Vani {i}", Gender.female,
                                     28, **perfect) for i in range(2)]
        legacy = await _add_member("+919730005303", "Legacy Lalitha", Gender.female, 28, **perfect)
        # Created last, so the newest perfect match: first in any tie
        hidden = await _add_member("+919730005304", "Hidden Hema", Gender.female, 28,
                                   hide_from_search=True, **perfect)
        # Legacy rows have no hide_from_search value: NULL means not hidden
        async with async_session() as session:
            await session.execute(
                update(Profile).where(Profile.id == legacy).values(hide_from_search=None)
            )
            await session.commit()
            assert await session.scalar(
                select(Profile.hide_from_search).where(Profile.id == legacy)
            ) is None

        # Small pool: the hidden member must not take one of the three places
        monkeypatch.setattr(settings, "MATCH_CANDIDATE_POOL", 3)
        assert {pid for pid, _ in await _recommendations(p_seeker["id"])} == {*visible, legacy}

        # Through the API, with the default pool
        monkeypatch.setattr(settings, "MATCH_CANDIDATE_POOL", 300)
        resp = await seeker.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        rec_ids = {r["profile"]["id"] for r in resp.json()}
        assert {*visible, legacy} <= rec_ids
        assert hidden not in rec_ids and "Hidden Hema" not in resp.text

        # Weekly digest (same recommendations): the hidden member is left out there too
        async with async_session() as session:
            await session.execute(
                update(User).where(User.phone == "+919730005300")
                .values(email=f"{tag}@example.com", email_digest_opt_in=True)
            )
            await session.commit()
        sent: dict[str, str] = {}

        async def fake_send_email(to: str, subject: str, html: str) -> bool:
            sent[to] = html
            return True

        monkeypatch.setattr(digest_service, "send_email", fake_send_email)
        async with async_session() as session:
            await digest_service.send_weekly_digest(session)
        digest = sent[f"{tag}@example.com"]
        assert "Visible Vani" in digest and "Hidden Hema" not in digest

        # Unhiding brings her back
        async with async_session() as session:
            await session.execute(
                update(Profile).where(Profile.id == hidden).values(hide_from_search=False)
            )
            await session.commit()
        resp = await seeker.get("/api/matches/recommendations?limit=200")
        assert hidden in {r["profile"]["id"] for r in resp.json()}
    finally:
        await seeker.aclose()


@pytest.mark.asyncio
async def test_sql_prescore_matches_python_score():
    """The database ranking gives each candidate exactly calculate_score's points
    (with height bounds set there are no constant points), NULL fields and the
    age boundaries included."""
    tag = f"pool{uuid.uuid4().hex[:8]}"
    state = f"Mirrorpradesh {tag}"
    wanted, other = await _communities(tag, 2)
    pref = Preference(min_age=25, max_age=32, min_height=150, max_height=170,
                      marital_status=["never_married", "widowed", "not-a-status"],
                      community_id=[wanted, "junk"], state=state)

    base = "+91973000540"
    ids = [
        await _add_member(f"{base}0", "Mirror All", Gender.female, 28, height_cm=160,
                          marital_status=MaritalStatus.widowed, community_id=wanted, state=state),
        await _add_member(f"{base}1", "Mirror Nulls", Gender.female, 28),
        await _add_member(f"{base}2", "Mirror Edge Low", Gender.female, 25, height_cm=150,
                          marital_status=MaritalStatus.divorced, community_id=other,
                          state=state.upper()),
        await _add_member(f"{base}3", "Mirror Edge High", Gender.female, 32, height_cm=170,
                          state=state),
        await _add_member(f"{base}4", "Mirror Too Old", Gender.female, 33, height_cm=171,
                          marital_status=MaritalStatus.never_married, community_id=wanted),
        await _add_member(f"{base}5", "Mirror Too Young", Gender.female, 24, height_cm=149),
    ]
    async with async_session() as session:
        # Born one day later than exactly-33 is still 32; one day later than 25 is 24
        await session.execute(update(Profile).where(Profile.id == ids[3]).values(
            date_of_birth=years_ago(33) + timedelta(days=1)))
        await session.execute(update(Profile).where(Profile.id == ids[5]).values(
            date_of_birth=years_ago(25) + timedelta(days=1)))
        await session.commit()

        prescore = MatchingService.preference_prescore(pref)
        rows = (await session.execute(
            select(Profile, prescore).options(selectinload(Profile.horoscope))
            .where(Profile.id.in_(ids))
        )).all()

    assert len(rows) == len(ids)
    by_name = {}
    for profile, sql_points in rows:
        score, _reasons, _confidence = MatchingService.calculate_score(profile, pref)
        assert sql_points == score, profile.display_name
        by_name[profile.display_name] = score
    assert by_name["Mirror All"] == 100
    assert by_name["Mirror Nulls"] == 25            # age only; NULLs earn nothing
    assert by_name["Mirror Edge Low"] == 25 + 15    # bounds inclusive, state case-sensitive
    assert by_name["Mirror Edge High"] == 25 + 15 + 20
    assert by_name["Mirror Too Old"] == 20 + 20
    assert by_name["Mirror Too Young"] == 0
