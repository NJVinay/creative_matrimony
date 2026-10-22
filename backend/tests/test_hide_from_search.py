""""Hide completely from Search" (Profile.hide_from_search): a hidden member is
left out of search results and totals, comes back when unhidden, and the
setting round-trips through /api/profiles/me so the settings page shows it."""

import pytest
from sqlalchemy import update

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.profile import Profile


async def _search(client, **filters) -> tuple[dict[int, dict], int, str]:
    """POST /api/search; returns (results by profile id, total, raw body)."""
    resp = await client.post("/api/search", json={"min_age": 18, "max_age": 99, "limit": 50, **filters})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return {p["id"]: p for p in body["results"]}, body["total"], resp.text


async def _set_hidden(client, hidden: bool) -> None:
    resp = await client.patch("/api/profiles/me/privacy", json={"hide_from_search": hidden})
    assert resp.status_code == 200, resp.text
    assert resp.json()["hide_from_search"] is hidden


async def _my_hide_flag(client):
    resp = await client.get("/api/profiles/me")
    assert resp.status_code == 200, resp.text
    return resp.json()["hide_from_search"]


@pytest.mark.asyncio
async def test_hidden_member_left_out_of_search_until_unhidden():
    seeker = await make_client("+919720000501")
    hider = await make_client("+919720000502")
    other = await make_client("+919720000503")
    try:
        p_seeker = await create_profile(seeker, display_name="Seeker Srinivas", gender="male",
                                        city_village="Hidesearchpeta")
        p_hider = await create_profile(hider, display_name="Hider Hamsa", gender="female",
                                       city_village="Hidesearchpeta")
        p_other = await create_profile(other, display_name="Other Oormila", gender="female",
                                       city_village="Hidesearchpeta")
        assert await _my_hide_flag(hider) is False

        results, total, _ = await _search(seeker, gender="female", city_village="Hidesearchpeta")
        assert results.keys() == {p_hider["id"], p_other["id"]} and total == 2

        await _set_hidden(hider, True)
        # /profiles/me reports it, so the settings checkbox reloads ticked
        assert await _my_hide_flag(hider) is True

        # Gone from another member's results and from the total
        results, total, text = await _search(seeker, gender="female", city_village="Hidesearchpeta")
        assert results.keys() == {p_other["id"]} and total == 1
        assert "Hider Hamsa" not in text
        # A one-per-page search never pages into the hidden profile
        resp = await seeker.post("/api/search", json={
            "min_age": 18, "max_age": 99, "gender": "female",
            "city_village": "Hidesearchpeta", "limit": 1, "page": 2,
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["results"] == [] and resp.json()["total"] == 1

        # Search never lists the searcher themselves, hidden or not; and hiding
        # only takes the hider out of search, it does not stop her searching
        results, total, _ = await _search(hider, gender="female", city_village="Hidesearchpeta")
        assert results.keys() == {p_other["id"]} and total == 1
        results, total, _ = await _search(hider, gender="male", city_village="Hidesearchpeta")
        assert results.keys() == {p_seeker["id"]} and total == 1

        # It is a search opt-out, not the "hidden" visibility: the profile page still opens
        resp = await seeker.get(f"/api/profiles/{p_hider['id']}")
        assert resp.status_code == 200, resp.text

        await _set_hidden(hider, False)
        assert await _my_hide_flag(hider) is False
        results, total, _ = await _search(seeker, gender="female", city_village="Hidesearchpeta")
        assert results.keys() == {p_hider["id"], p_other["id"]} and total == 2
    finally:
        for c in (seeker, hider, other):
            await c.aclose()


@pytest.mark.asyncio
async def test_legacy_null_hide_flag_counts_as_not_hidden():
    seeker = await make_client("+919720000511")
    legacy = await make_client("+919720000512")
    try:
        await create_profile(seeker, display_name="Seeker Sudheer", gender="male",
                             city_village="Nullhidepeta")
        p_legacy = await create_profile(legacy, display_name="Legacy Lavanya", gender="female",
                                        city_village="Nullhidepeta")
        async with async_session() as session:
            await session.execute(
                update(Profile).where(Profile.id == p_legacy["id"]).values(hide_from_search=None)
            )
            await session.commit()

        results, total, _ = await _search(seeker, gender="female", city_village="Nullhidepeta")
        assert results.keys() == {p_legacy["id"]} and total == 1
        assert await _my_hide_flag(legacy) is False
    finally:
        for c in (seeker, legacy):
            await c.aclose()
