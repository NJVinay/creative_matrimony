"""Legal minimum marriage age (India: 18 for women, 21 for men) — child safety."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.profile import Profile, Gender, ProfileMode
from app.models.user import User
from app.services.matching_service import MatchingService
from app.services.profile_service import meets_minimum_age, years_ago


def _iso(d: date) -> str:
    return d.isoformat()


def test_meets_minimum_age_boundaries():
    today = date(2026, 10, 22)
    assert meets_minimum_age(date(2008, 10, 22), "female", today)      # 18 today
    assert not meets_minimum_age(date(2008, 10, 23), "female", today)  # 18 tomorrow
    assert meets_minimum_age(date(2005, 10, 22), Gender.male, today)   # 21 today
    assert not meets_minimum_age(date(2005, 10, 23), "male", today)
    assert not meets_minimum_age(date(2006, 1, 1), "other", today)     # stricter bound
    assert not meets_minimum_age(None, "female", today)
    # 29 Feb never crashes the date arithmetic
    assert years_ago(18, date(2028, 2, 29)) == date(2010, 2, 28)


@pytest.mark.asyncio
@pytest.mark.parametrize("phone,gender,dob,expected", [
    ("+919400000001", "female", years_ago(18) + timedelta(days=1), 422),  # 17
    ("+919400000002", "female", years_ago(18), 201),                      # exactly 18
    ("+919400000003", "male", years_ago(21) + timedelta(days=1), 422),    # 20
    ("+919400000004", "male", years_ago(21), 201),                        # exactly 21
    ("+919400000005", "other", years_ago(20), 422),
    ("+919400000006", "female", date(2015, 3, 1), 422),                   # QA repro
    ("+919400000007", "male", date.today() + timedelta(days=30), 422),    # future
])
async def test_create_profile_enforces_legal_age(phone, gender, dob, expected):
    client = await make_client(phone)
    try:
        resp = await client.post("/api/profiles", json={
            "profile_mode": "self", "display_name": "Age Check", "gender": gender,
            "date_of_birth": _iso(dob), "city_village": "Guntur", "state": "Andhra Pradesh",
        })
        assert resp.status_code == expected, resp.text
        if expected == 422:
            error = resp.json()["detail"][0]
            assert error["loc"][-1] == "date_of_birth"
            assert "years old" in error["msg"] or "future" in error["msg"]
        if gender == "male" and expected == 422 and dob < date.today():
            assert "at least 21" in resp.json()["detail"][0]["msg"]
    finally:
        await client.aclose()


async def _insert_legacy_profile(phone: str, name: str, gender: Gender, dob: date) -> int:
    """A profile created before the DOB check existed (bypasses the API)."""
    client = await make_client(phone)
    await client.aclose()
    async with async_session() as session:
        user_id = await session.scalar(select(User.id).where(User.phone == phone))
        profile = Profile(
            user_id=user_id, profile_mode=ProfileMode.self_managed, display_name=name,
            gender=gender, date_of_birth=dob, city_village="Hyderabad", state="Telangana",
            completion_pct=60.0, is_active=True,
        )
        session.add(profile)
        await session.commit()
        return profile.id


@pytest.mark.asyncio
async def test_recommendations_and_search_hard_exclude_minors():
    seeker = await make_client("+919400000010")      # 31-year-old man
    seeker_f = await make_client("+919400000011")    # 30-year-old woman
    try:
        p_seeker = await create_profile(seeker, display_name="Seeker Man", gender="male",
                                        date_of_birth="1995-01-15")
        p_seeker_f = await create_profile(seeker_f, display_name="Seeker Woman", gender="female",
                                          date_of_birth="1996-01-15")
        adult_f = await _insert_legacy_profile("+919400000012", "Adult Woman", Gender.female,
                                               years_ago(18))
        minor_f = await _insert_legacy_profile("+919400000013", "Minor Girl", Gender.female,
                                               years_ago(11))
        minor_m = await _insert_legacy_profile("+919400000014", "Young Man", Gender.male,
                                               years_ago(19))

        # Preferences that would *score* a minor highly must still not surface one
        resp = await seeker.put("/api/matches/preferences", json={"min_age": 0, "max_age": 99})
        assert resp.status_code == 200, resp.text

        resp = await seeker.get("/api/matches/recommendations")
        assert resp.status_code == 200, resp.text
        rec_ids = {r["profile"]["id"] for r in resp.json()}
        assert adult_f in rec_ids
        assert minor_f not in rec_ids

        resp = await seeker_f.get("/api/matches/recommendations")
        assert resp.status_code == 200, resp.text
        rec_ids_f = {r["profile"]["id"] for r in resp.json()}
        assert p_seeker["id"] in rec_ids_f
        assert minor_m not in rec_ids_f  # 19-year-old man: below 21

        resp = await seeker.post("/api/search", json={"min_age": 18, "max_age": 99, "gender": "female",
                                                      "limit": 50})
        assert resp.status_code == 200, resp.text
        search_ids = {p["id"] for p in resp.json()["results"]}
        assert adult_f in search_ids and minor_f not in search_ids

        resp = await seeker_f.post("/api/search", json={"min_age": 18, "max_age": 99, "gender": "male",
                                                        "limit": 50})
        assert minor_m not in {p["id"] for p in resp.json()["results"]}
        assert p_seeker_f["id"] not in {p["id"] for p in resp.json()["results"]}
    finally:
        await seeker.aclose()
        await seeker_f.aclose()


@pytest.mark.asyncio
async def test_legacy_minor_gets_no_matches_and_is_deactivated_on_edit():
    phone = "+919400000020"
    minor_id = await _insert_legacy_profile(phone, "Legacy Minor", Gender.female, years_ago(12))
    async with async_session() as session:
        assert await MatchingService.get_recommendations(session, minor_id) == []

    client = await make_client(phone)
    try:
        resp = await client.patch("/api/profiles/me", json={"bio": "Updated bio"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_active"] is False
    finally:
        await client.aclose()
