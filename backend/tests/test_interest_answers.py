"""Answering interests: only a pending interest can be accepted or declined,
once, and a pair never ends up with two chat rooms."""

import asyncio

import pytest
from sqlalchemy import func, select

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.communication import ChatParticipant, ChatRoom, Interest


async def _status(interest_id: int) -> str:
    async with async_session() as session:
        return (await session.get(Interest, interest_id)).status


async def _rooms(client) -> list[int]:
    resp = await client.get("/api/chat/rooms")
    assert resp.status_code == 200, resp.text
    return [r["id"] for r in resp.json()]


async def _rooms_in_db(user_id: int) -> int:
    async with async_session() as session:
        return await session.scalar(
            select(func.count(ChatRoom.id))
            .join(ChatParticipant, ChatParticipant.room_id == ChatRoom.id)
            .where(ChatParticipant.user_id == user_id)
        )


async def _send(sender, receiver_profile_id: int) -> int:
    resp = await sender.post(f"/api/interests/{receiver_profile_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_only_a_pending_interest_can_be_answered():
    """Regression: accept and reject set the status whatever it was, so a
    declined interest could be accepted later and an accepted one accepted
    again, each accept opening another chat room."""
    him = await make_client("+919730000001")
    her = await make_client("+919730000002")
    other = await make_client("+919730000003")
    try:
        await create_profile(him, display_name="Answer Arun", gender="male")
        p_her = await create_profile(her, display_name="Answer Anu", gender="female")
        await create_profile(other, display_name="Answer Ajay", gender="male")

        # Declined stays declined
        declined = await _send(him, p_her["id"])
        resp = await her.put(f"/api/interests/{declined}/reject")
        assert resp.status_code == 200, resp.text
        for action in ("accept", "reject"):
            resp = await her.put(f"/api/interests/{declined}/{action}")
            assert resp.status_code == 409, resp.text
            assert "already been answered" in resp.json()["detail"]
        assert await _status(declined) == "rejected"
        assert await _rooms(him) == []

        # Accepted works once; answering it again changes nothing
        accepted = await _send(other, p_her["id"])
        resp = await her.put(f"/api/interests/{accepted}/accept")
        assert resp.status_code == 200, resp.text
        rooms = await _rooms(other)
        assert len(rooms) == 1
        for action in ("accept", "reject"):
            resp = await her.put(f"/api/interests/{accepted}/{action}")
            assert resp.status_code == 409, resp.text
        assert await _status(accepted) == "accepted"
        assert await _rooms(other) == rooms == await _rooms(her)

        # The sender cannot answer their own interest
        resp = await other.put(f"/api/interests/{accepted}/accept")
        assert resp.status_code == 404, resp.text
    finally:
        for c in (him, her, other):
            await c.aclose()


@pytest.mark.asyncio
async def test_interests_both_ways_share_one_chat_room():
    him = await make_client("+919730000011")
    her = await make_client("+919730000012")
    try:
        p_him = await create_profile(him, display_name="Both Bharat", gender="male")
        p_her = await create_profile(her, display_name="Both Bhavya", gender="female")
        his = await _send(him, p_her["id"])
        hers = await _send(her, p_him["id"])

        assert (await her.put(f"/api/interests/{his}/accept")).status_code == 200
        assert (await him.put(f"/api/interests/{hers}/accept")).status_code == 200
        assert await _status(his) == await _status(hers) == "accepted"
        rooms = await _rooms(him)
        assert len(rooms) == 1 and await _rooms(her) == rooms
    finally:
        await him.aclose()
        await her.aclose()


@pytest.mark.asyncio
async def test_accepting_both_directions_at_once_opens_one_room():
    him = await make_client("+919730000031")
    her = await make_client("+919730000032")
    try:
        p_him = await create_profile(him, display_name="Same-time Sandeep", gender="male")
        p_her = await create_profile(her, display_name="Same-time Sravani", gender="female")
        his = await _send(him, p_her["id"])
        hers = await _send(her, p_him["id"])

        statuses = await asyncio.gather(
            her.put(f"/api/interests/{his}/accept"),
            him.put(f"/api/interests/{hers}/accept"),
        )
        assert [r.status_code for r in statuses] == [200, 200]
        him_id = (await him.get("/api/auth/me")).json()["id"]
        assert await _rooms_in_db(him_id) == 1
    finally:
        await him.aclose()
        await her.aclose()


@pytest.mark.asyncio
async def test_parallel_accepts_open_one_room():
    him = await make_client("+919730000021")
    her = await make_client("+919730000022")
    try:
        await create_profile(him, display_name="Parallel Pavan", gender="male")
        p_her = await create_profile(her, display_name="Parallel Pallavi", gender="female")
        interest = await _send(him, p_her["id"])

        statuses = await asyncio.gather(*(
            her.put(f"/api/interests/{interest}/accept") for _ in range(5)
        ))
        assert sorted(r.status_code for r in statuses) == [200] + [409] * 4
        him_id = (await him.get("/api/auth/me")).json()["id"]
        assert await _rooms_in_db(him_id) == 1
    finally:
        await him.aclose()
        await her.aclose()
