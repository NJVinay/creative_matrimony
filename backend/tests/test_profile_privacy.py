"""Who may see a profile, its photos and horoscope charts:
legal age, server-side photo blur, blocks, admin/moderator review, match and
search photos, interests and chat with minors, and the under-age cleanup script."""

import importlib.util
import pathlib
import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select, update

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.communication import ChatMessage, ChatParticipant, ChatRoom, Interest, InterestStatus
from app.models.horoscope import Horoscope
from app.models.profile import Profile, ProfilePhoto, Gender, ProfileMode, Visibility
from app.models.user import User, UserRole
from app.services.profile_service import photo_viewable_profile_ids, years_ago


def _load_cleanup_script():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "deactivate_underage_profiles.py"
    spec = importlib.util.spec_from_file_location("deactivate_underage_profiles", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _set_role(phone: str, role: UserRole) -> None:
    async with async_session() as session:
        await session.execute(update(User).where(User.phone == phone).values(role=role))
        await session.commit()


async def _insert_legacy_profile(phone: str, name: str, gender: Gender, dob: date) -> int:
    """A profile created before the DOB check existed (bypasses the API)."""
    client = await make_client(phone)
    await client.aclose()
    async with async_session() as session:
        user_id = await session.scalar(select(User.id).where(User.phone == phone))
        profile = Profile(
            user_id=user_id, profile_mode=ProfileMode.self_managed, display_name=name,
            gender=gender, date_of_birth=dob, city_village="Hyderabad", state="Telangana",
            completion_pct=60.0, is_active=True, visibility=Visibility.public,
        )
        session.add(profile)
        await session.commit()
        return profile.id


async def _add_photo(profile_id: int, *, is_primary: bool = False, approved: bool | None = True,
                     created_at: datetime | None = None) -> str:
    """Insert a photo row directly (no file on disk); returns its storage key."""
    key = f"uploads/profiles/profile_test_{uuid.uuid4().hex}.jpg"
    async with async_session() as session:
        photo = ProfilePhoto(profile_id=profile_id, storage_key=key,
                             is_primary=is_primary, is_approved=approved)
        if created_at is not None:
            photo.created_at = created_at
        session.add(photo)
        await session.commit()
    return key


async def _add_horoscope(profile_id: int) -> str:
    chart = f"/uploads/horoscopes/test_{uuid.uuid4().hex}.png"
    async with async_session() as session:
        session.add(Horoscope(profile_id=profile_id, dosham=False, chart_images=[chart]))
        await session.commit()
    return chart


async def _mutual_interest(sender, receiver, receiver_profile_id: int) -> None:
    resp = await sender.post(f"/api/interests/{receiver_profile_id}")
    assert resp.status_code == 200, resp.text
    resp = await receiver.put(f"/api/interests/{resp.json()['id']}/accept")
    assert resp.status_code == 200, resp.text


async def _user_id(phone: str) -> int:
    async with async_session() as session:
        return await session.scalar(select(User.id).where(User.phone == phone))


async def _set_verified(phone: str) -> None:
    async with async_session() as session:
        await session.execute(update(User).where(User.phone == phone).values(is_verified=True))
        await session.commit()


async def _insert_interest(sender_id: int, receiver_id: int,
                           status: InterestStatus = InterestStatus.pending) -> int:
    """An interest row written directly, like one sent before the age check existed."""
    async with async_session() as session:
        interest = Interest(sender_id=sender_id, receiver_id=receiver_id, status=status.value)
        session.add(interest)
        await session.commit()
        return interest.id


async def _insert_chat_room(*user_ids: int, message_from: int | None = None) -> int:
    """An open chat room between the given users, written directly (legacy row),
    optionally with one message from `message_from`."""
    async with async_session() as session:
        room = ChatRoom(is_active=True)
        session.add(room)
        await session.flush()
        session.add_all([ChatParticipant(room_id=room.id, user_id=uid) for uid in user_ids])
        if message_from is not None:
            session.add(ChatMessage(room_id=room.id, sender_id=message_from,
                                    content="Sent before the age check existed"))
        await session.commit()
        return room.id


async def _interest_status(interest_id: int) -> str:
    async with async_session() as session:
        return (await session.get(Interest, interest_id)).status


async def _room_is_active(room_id: int) -> bool:
    async with async_session() as session:
        return (await session.get(ChatRoom, room_id)).is_active


async def _search(client, **filters) -> tuple[dict[int, dict], int, str]:
    """POST /api/search; returns (results by profile id, total, raw body)."""
    resp = await client.post("/api/search", json={"min_age": 18, "max_age": 99, "limit": 50, **filters})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return {p["id"]: p for p in body["results"]}, body["total"], resp.text


@pytest.mark.asyncio
async def test_underage_profile_is_404_for_members_but_reviewable_by_staff():
    member = await make_client("+919700000001")
    admin = await make_client("+919700000002")      # no profile of their own
    moderator = await make_client("+919700000003")
    try:
        await create_profile(member, display_name="Member Mahesh", gender="male")
        await _set_role("+919700000002", UserRole.admin)
        await _set_role("+919700000003", UserRole.moderator)

        minor_id = await _insert_legacy_profile("+919700000004", "Legacy Minor", Gender.female,
                                                years_ago(16))
        photo_key = await _add_photo(minor_id, is_primary=True)
        await _add_horoscope(minor_id)
        # 20-year-old man: an adult, but below the legal marriage age for men
        young_man_id = await _insert_legacy_profile("+919700000005", "Young Man", Gender.male,
                                                    years_ago(20))

        for path in (f"/api/profiles/{minor_id}", f"/api/profiles/{minor_id}/photos",
                     f"/api/horoscope/profile/{minor_id}", f"/api/profiles/{young_man_id}"):
            resp = await member.get(path)
            assert resp.status_code == 404, (path, resp.text)

        for staff in (admin, moderator):
            resp = await staff.get(f"/api/profiles/{minor_id}")
            assert resp.status_code == 200, resp.text
            assert resp.json()["display_name"] == "Legacy Minor"
            resp = await staff.get(f"/api/profiles/{minor_id}/photos")
            assert resp.status_code == 200, resp.text
            assert [p["storage_key"] for p in resp.json()] == [photo_key]
            resp = await staff.get(f"/api/horoscope/profile/{minor_id}")
            assert resp.status_code == 200, resp.text
    finally:
        for c in (member, admin, moderator):
            await c.aclose()


@pytest.mark.asyncio
async def test_photo_blur_is_enforced_by_the_api():
    her = await make_client("+919700000010")
    stranger = await make_client("+919700000011")
    mutual = await make_client("+919700000012")     # he sent, she accepted
    mutual_rev = await make_client("+919700000013")  # she sent, he accepted
    try:
        p_her = await create_profile(her, display_name="Blurred Bhavani", gender="female")
        assert p_her["photo_blur_until_mutual"] is True  # women-first default
        p_stranger = await create_profile(stranger, display_name="Stranger Suresh", gender="male")
        await create_profile(mutual, display_name="Mutual Murali", gender="male")
        p_rev = await create_profile(mutual_rev, display_name="Reverse Ravi", gender="male")

        her_id = p_her["id"]
        primary = await _add_photo(her_id, is_primary=True)
        second = await _add_photo(her_id)
        await _add_photo(her_id, approved=None)  # pending: never listed publicly
        chart = await _add_horoscope(her_id)

        # A pending (not accepted) interest does not unlock anything
        resp = await stranger.post(f"/api/interests/{her_id}")
        assert resp.status_code == 200, resp.text

        resp = await stranger.get(f"/api/profiles/{her_id}/photos")
        assert resp.status_code == 200, resp.text
        photos = resp.json()
        assert len(photos) == 2
        assert all(p["storage_key"] is None and p["locked"] is True for p in photos)
        assert primary not in resp.text and second not in resp.text

        resp = await stranger.get(f"/api/horoscope/profile/{her_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["chart_images"] == []
        assert resp.json()["charts_locked"] is True
        assert chart not in resp.text

        await _mutual_interest(mutual, her, her_id)
        await _mutual_interest(her, mutual_rev, p_rev["id"])

        for viewer in (her, mutual, mutual_rev):  # owner + both interest directions
            resp = await viewer.get(f"/api/profiles/{her_id}/photos")
            assert resp.status_code == 200, resp.text
            assert {p["storage_key"] for p in resp.json()} == {primary, second}
            assert not any(p["locked"] for p in resp.json())
            resp = await viewer.get(f"/api/horoscope/profile/{her_id}")
            assert resp.status_code == 200, resp.text
            assert resp.json()["chart_images"] == [chart]
            assert resp.json()["charts_locked"] is False

        # Turning blur off unlocks for everyone
        resp = await her.patch("/api/profiles/me/privacy", json={"photo_blur_until_mutual": False})
        assert resp.status_code == 200, resp.text
        resp = await stranger.get(f"/api/profiles/{her_id}/photos")
        assert {p["storage_key"] for p in resp.json()} == {primary, second}

        # A profile without blur is visible to anyone who can see the profile
        stranger_photo = await _add_photo(p_stranger["id"])
        resp = await her.get(f"/api/profiles/{p_stranger['id']}/photos")
        assert [p["storage_key"] for p in resp.json()] == [stranger_photo]
    finally:
        for c in (her, stranger, mutual, mutual_rev):
            await c.aclose()


@pytest.mark.asyncio
async def test_blocked_viewer_gets_403_on_photos_and_horoscope():
    alice = await make_client("+919700000020")
    bob = await make_client("+919700000021")
    try:
        p_alice = await create_profile(alice, display_name="Alice Block", gender="female")
        p_bob = await create_profile(bob, display_name="Bob Block", gender="male")
        await _add_photo(p_alice["id"])
        await _add_horoscope(p_alice["id"])
        await _add_horoscope(p_bob["id"])

        resp = await bob.get(f"/api/horoscope/profile/{p_alice['id']}")
        assert resp.status_code == 200, resp.text

        resp = await alice.post(f"/api/safety/block/{p_bob['id']}", json={"reason": "test"})
        assert resp.status_code == 201, resp.text

        for path in (f"/api/profiles/{p_alice['id']}/photos", f"/api/horoscope/profile/{p_alice['id']}"):
            resp = await bob.get(path)
            assert resp.status_code == 403, (path, resp.text)
        # ...and in the other direction
        resp = await alice.get(f"/api/horoscope/profile/{p_bob['id']}")
        assert resp.status_code == 403
        resp = await alice.get(f"/api/profiles/{p_bob['id']}/photos")
        assert resp.status_code == 403
    finally:
        await alice.aclose()
        await bob.aclose()


@pytest.mark.asyncio
async def test_admin_can_review_hidden_verified_only_and_blocking_profiles():
    member = await make_client("+919700000030")
    admin = await make_client("+919700000031")         # no profile, not verified
    admin_member = await make_client("+919700000032")  # admin who also has a profile
    hidden = await make_client("+919700000033")
    verified_only = await make_client("+919700000034")
    try:
        await create_profile(member, display_name="Member Mohan", gender="male")
        p_admin_member = await create_profile(admin_member, display_name="Admin Arjun", gender="male")
        p_hidden = await create_profile(hidden, display_name="Hidden Hema", gender="female")
        p_vo = await create_profile(verified_only, display_name="Verified Vani", gender="female",
                                    verified_only_opt_in=True)
        await _set_role("+919700000031", UserRole.admin)
        await _set_role("+919700000032", UserRole.admin)

        resp = await hidden.patch("/api/profiles/me/privacy", json={"visibility": "hidden"})
        assert resp.status_code == 200, resp.text
        hidden_photo = await _add_photo(p_hidden["id"])
        hidden_chart = await _add_horoscope(p_hidden["id"])

        for path in (f"/api/profiles/{p_hidden['id']}", f"/api/profiles/{p_hidden['id']}/photos",
                     f"/api/horoscope/profile/{p_hidden['id']}", f"/api/profiles/{p_vo['id']}"):
            resp = await member.get(path)
            assert resp.status_code == 403, (path, resp.text)

        # Reported hidden profile: the admin reports page links here
        resp = await admin.get(f"/api/profiles/{p_hidden['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["display_name"] == "Hidden Hema"
        resp = await admin.get(f"/api/profiles/{p_hidden['id']}/photos")
        assert resp.status_code == 200, resp.text
        # Blur is on (female default) but staff review sees the real photo
        assert [p["storage_key"] for p in resp.json()] == [hidden_photo]
        resp = await admin.get(f"/api/horoscope/profile/{p_hidden['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["chart_images"] == [hidden_chart]

        resp = await admin.get(f"/api/profiles/{p_vo['id']}")
        assert resp.status_code == 200, resp.text

        # A member who blocked the admin's own account is still reviewable
        await _add_horoscope(p_vo["id"])
        resp = await verified_only.post(f"/api/safety/block/{p_admin_member['id']}", json={})
        assert resp.status_code == 201, resp.text
        for path in (f"/api/profiles/{p_vo['id']}", f"/api/profiles/{p_vo['id']}/photos",
                     f"/api/horoscope/profile/{p_vo['id']}"):
            resp = await admin_member.get(path)
            assert resp.status_code == 200, (path, resp.text)
    finally:
        for c in (member, admin, admin_member, hidden, verified_only):
            await c.aclose()


@pytest.mark.asyncio
async def test_recommendations_carry_profile_photo_only_when_allowed():
    seeker = await make_client("+919700000040")
    open_f = await make_client("+919700000041")
    recent_f = await make_client("+919700000042")
    blurred_f = await make_client("+919700000043")
    pending_f = await make_client("+919700000044")
    reviewer = await make_client("+919700000045")
    try:
        await create_profile(seeker, display_name="Seeker Sai", gender="male")
        await create_profile(reviewer, display_name="Reviewer Ramu", gender="male")
        await _set_role("+919700000045", UserRole.moderator)
        p_open = await create_profile(open_f, display_name="Open Oormila", gender="female")
        p_recent = await create_profile(recent_f, display_name="Recent Rekha", gender="female")
        p_blurred = await create_profile(blurred_f, display_name="Blurred Bindu", gender="female")
        p_pending = await create_profile(pending_f, display_name="Pending Padma", gender="female")
        for c in (open_f, recent_f, pending_f):
            resp = await c.patch("/api/profiles/me/privacy", json={"photo_blur_until_mutual": False})
            assert resp.status_code == 200, resp.text

        now = datetime.utcnow().replace(microsecond=0)
        open_primary = await _add_photo(p_open["id"], is_primary=True, created_at=now - timedelta(days=2))
        await _add_photo(p_open["id"], created_at=now)  # newer, but not primary
        await _add_photo(p_recent["id"], created_at=now - timedelta(days=3))
        recent_newest = await _add_photo(p_recent["id"], created_at=now - timedelta(days=1))
        await _add_photo(p_recent["id"], approved=False, created_at=now)  # rejected: ignored
        blurred_photo = await _add_photo(p_blurred["id"], is_primary=True)
        await _add_photo(p_pending["id"], approved=None)

        for c in (seeker, reviewer):
            resp = await c.put("/api/matches/preferences", json={"min_age": 18, "max_age": 99})
            assert resp.status_code == 200, resp.text

        resp = await seeker.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        recs = {r["profile"]["id"]: r["profile"] for r in resp.json()}
        assert {p_open["id"], p_recent["id"], p_blurred["id"], p_pending["id"]} <= recs.keys()
        assert recs[p_open["id"]]["profile_photo"] == {"url": f"/{open_primary}"}
        assert recs[p_recent["id"]]["profile_photo"] == {"url": f"/{recent_newest}"}
        assert recs[p_blurred["id"]]["profile_photo"] is None
        assert recs[p_blurred["id"]]["photo_blur_until_mutual"] is True
        assert recs[p_blurred["id"]]["photo_locked"] is True
        # No approved photo yet is not a lock: the client shows a plain placeholder
        assert recs[p_pending["id"]]["profile_photo"] is None
        assert recs[p_pending["id"]]["photo_locked"] is False
        assert recs[p_open["id"]]["photo_locked"] is False
        assert blurred_photo not in resp.text

        # Staff bypass photo blur here too
        resp = await reviewer.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        recs = {r["profile"]["id"]: r["profile"] for r in resp.json()}
        assert recs[p_blurred["id"]]["profile_photo"] == {"url": f"/{blurred_photo}"}

        # Endpoints that do not resolve photo access fill neither photo field
        resp = await seeker.get(f"/api/profiles/{p_blurred['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["profile_photo"] is None
        assert resp.json()["photo_locked"] is False
    finally:
        for c in (seeker, open_f, recent_f, blurred_f, pending_f, reviewer):
            await c.aclose()


@pytest.mark.asyncio
async def test_adult_cannot_interest_or_chat_with_underage_profile():
    """Legacy minors stay active and public until the cleanup script runs, so
    interests and chat must refuse them on their own. An adult inserted the
    same way is the control: the same calls succeed for her."""
    adult = await make_client("+919710000001")
    try:
        p_adult = await create_profile(adult, display_name="Adult Anand", gender="male")
        minor_id = await _insert_legacy_profile("+919710000002", "Legacy Meena", Gender.female,
                                                years_ago(16))
        woman_id = await _insert_legacy_profile("+919710000003", "Legacy Aruna", Gender.female,
                                                years_ago(25))
        adult_uid = await _user_id("+919710000001")
        minor_uid = await _user_id("+919710000002")
        woman_uid = await _user_id("+919710000003")

        # Sending: the minor does not exist as far as members are concerned
        resp = await adult.post(f"/api/interests/{minor_id}")
        assert resp.status_code == 404, resp.text
        async with async_session() as session:
            assert await session.scalar(select(Interest.id).where(
                Interest.sender_id == p_adult["id"], Interest.receiver_id == minor_id)) is None
        resp = await adult.post(f"/api/interests/{woman_id}")
        assert resp.status_code == 200, resp.text

        # Interests written before the age check existed: not listed, not acceptable
        from_minor = await _insert_interest(minor_id, p_adult["id"])
        to_minor = await _insert_interest(p_adult["id"], minor_id)
        from_woman = await _insert_interest(woman_id, p_adult["id"])
        resp = await adult.get("/api/interests/received")
        assert resp.status_code == 200, resp.text
        received = {i["id"] for i in resp.json()}
        assert from_woman in received and from_minor not in received
        resp = await adult.get("/api/interests/sent")
        assert resp.status_code == 200, resp.text
        assert to_minor not in {i["id"] for i in resp.json()}
        assert "Legacy Meena" not in resp.text

        resp = await adult.put(f"/api/interests/{from_minor}/accept")
        assert resp.status_code == 404, resp.text
        assert await _interest_status(from_minor) == InterestStatus.pending.value
        resp = await adult.put(f"/api/interests/{from_woman}/accept")
        assert resp.status_code == 200, resp.text

        # A chat room opened before the age check existed is closed for everyone
        minor_room = await _insert_chat_room(adult_uid, minor_uid, message_from=minor_uid)
        resp = await adult.get("/api/chat/rooms")
        assert resp.status_code == 200, resp.text
        rooms = {r["id"]: {p["user_id"] for p in r["participants"]} for r in resp.json()}
        assert minor_room not in rooms
        woman_rooms = [rid for rid, users in rooms.items() if users == {adult_uid, woman_uid}]
        assert len(woman_rooms) == 1  # created by accepting her interest

        resp = await adult.get(f"/api/chat/rooms/{minor_room}/messages")
        assert resp.status_code == 200, resp.text
        assert resp.json() == []
        resp = await adult.post(f"/api/chat/rooms/{minor_room}/messages", json={"content": "Hello"})
        assert resp.status_code == 403, resp.text
        resp = await adult.post(f"/api/chat/rooms/{woman_rooms[0]}/messages", json={"content": "Hello"})
        assert resp.status_code == 200, resp.text
        resp = await adult.get(f"/api/chat/rooms/{woman_rooms[0]}/messages")
        assert [m["content"] for m in resp.json()] == ["Hello"]
    finally:
        await adult.aclose()


@pytest.mark.asyncio
async def test_verified_only_photo_reaches_only_verified_viewers():
    unverified = await make_client("+919710000020")
    verified = await make_client("+919710000021")
    vo = await make_client("+919710000022")
    try:
        await create_profile(unverified, display_name="Unverified Umesh", gender="male")
        await create_profile(verified, display_name="Verified Venkat", gender="male")
        await _set_verified("+919710000021")
        p_vo = await create_profile(vo, display_name="Verified-only Vasudha", gender="female",
                                    verified_only_opt_in=True, city_village="Vanipalem")
        assert p_vo["visibility"] == "verified_only"
        # Blur off, so only the verified-only rule can keep the photo back
        resp = await vo.patch("/api/profiles/me/privacy", json={"photo_blur_until_mutual": False})
        assert resp.status_code == 200, resp.text
        photo = await _add_photo(p_vo["id"], is_primary=True)
        for c in (unverified, verified):
            resp = await c.put("/api/matches/preferences", json={"min_age": 18, "max_age": 99})
            assert resp.status_code == 200, resp.text

        # Unverified viewer: the member is not offered at all, so neither is her photo
        resp = await unverified.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        assert p_vo["id"] not in {r["profile"]["id"] for r in resp.json()}
        assert photo not in resp.text
        results, total, text = await _search(unverified, gender="female", city_village="Vanipalem")
        assert p_vo["id"] not in results
        assert photo not in text

        # Verified viewer who may see her photos gets the URL in both lists
        resp = await verified.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        recs = {r["profile"]["id"]: r["profile"] for r in resp.json()}
        assert recs[p_vo["id"]]["profile_photo"] == {"url": f"/{photo}"}
        assert recs[p_vo["id"]]["photo_locked"] is False
        results, total, _ = await _search(verified, gender="female", city_village="Vanipalem")
        assert results[p_vo["id"]]["profile_photo"] == {"url": f"/{photo}"}
        assert results[p_vo["id"]]["photo_locked"] is False

        # The shared photo check refuses on its own, whatever list a caller builds
        async with async_session() as session:
            vo_profile = await session.get(Profile, p_vo["id"])
            for phone, expected in (("+919710000020", set()), ("+919710000021", {p_vo["id"]})):
                viewer = await session.scalar(select(User).where(User.phone == phone))
                assert await photo_viewable_profile_ids(session, viewer, [vo_profile]) == expected
    finally:
        for c in (unverified, verified, vo):
            await c.aclose()


@pytest.mark.asyncio
async def test_blocked_pair_hidden_from_search_and_interest_lists():
    her = await make_client("+919710000030")
    him = await make_client("+919710000031")
    other = await make_client("+919710000032")
    try:
        p_her = await create_profile(her, display_name="Blocker Bhargavi", gender="female",
                                     city_village="Blockpeta")
        p_him = await create_profile(him, display_name="Blocked Balaji", gender="male",
                                     city_village="Blockpeta")
        p_other = await create_profile(other, display_name="Other Ooha", gender="female",
                                       city_village="Blockpeta")
        resp = await him.post(f"/api/interests/{p_her['id']}")
        assert resp.status_code == 200, resp.text
        his_interest = resp.json()["id"]
        resp = await her.post(f"/api/interests/{p_him['id']}")
        assert resp.status_code == 200, resp.text
        her_interest = resp.json()["id"]

        async def listed(client, kind: str) -> set[int]:
            resp = await client.get(f"/api/interests/{kind}")
            assert resp.status_code == 200, resp.text
            return {i["id"] for i in resp.json()}

        # Before the block they find each other everywhere
        results, total, _ = await _search(him, gender="female", city_village="Blockpeta")
        assert results.keys() == {p_her["id"], p_other["id"]} and total == 2
        results, total, _ = await _search(her, gender="male", city_village="Blockpeta")
        assert results.keys() == {p_him["id"]} and total == 1
        assert his_interest in await listed(him, "sent") and his_interest in await listed(her, "received")
        assert her_interest in await listed(her, "sent") and her_interest in await listed(him, "received")

        resp = await her.post(f"/api/safety/block/{p_him['id']}", json={"reason": "test"})
        assert resp.status_code == 201, resp.text

        # After it, neither sees the other, in either direction (count included)
        results, total, text = await _search(him, gender="female", city_village="Blockpeta")
        assert results.keys() == {p_other["id"]} and total == 1
        assert "Blocker Bhargavi" not in text
        results, total, _ = await _search(her, gender="male", city_village="Blockpeta")
        assert results == {} and total == 0
        for client in (her, him):
            for kind in ("sent", "received"):
                assert not {his_interest, her_interest} & await listed(client, kind), kind
    finally:
        for c in (her, him, other):
            await c.aclose()


@pytest.mark.asyncio
async def test_search_photo_lock_follows_mutual_interest():
    her = await make_client("+919710000040")
    plain = await make_client("+919710000041")
    stranger = await make_client("+919710000042")
    mutual = await make_client("+919710000043")
    try:
        p_her = await create_profile(her, display_name="Lockpeta Lalitha", gender="female",
                                     city_village="Lockpeta")
        assert p_her["photo_blur_until_mutual"] is True  # women-first default
        p_plain = await create_profile(plain, display_name="Lockpeta Prasanna", gender="female",
                                       city_village="Lockpeta")
        resp = await plain.patch("/api/profiles/me/privacy", json={"photo_blur_until_mutual": False})
        assert resp.status_code == 200, resp.text
        await create_profile(stranger, display_name="Stranger Srinu", gender="male")
        await create_profile(mutual, display_name="Mutual Madhav", gender="male")
        her_photo = await _add_photo(p_her["id"], is_primary=True)
        plain_photo = await _add_photo(p_plain["id"], is_primary=True)

        # A pending interest unlocks nothing; an accepted one does
        resp = await stranger.post(f"/api/interests/{p_her['id']}")
        assert resp.status_code == 200, resp.text
        await _mutual_interest(mutual, her, p_her["id"])

        results, _, text = await _search(stranger, gender="female", city_village="Lockpeta")
        assert results[p_her["id"]]["photo_locked"] is True
        assert results[p_her["id"]]["profile_photo"] is None
        assert her_photo not in text
        assert results[p_plain["id"]]["photo_locked"] is False
        assert results[p_plain["id"]]["profile_photo"] == {"url": f"/{plain_photo}"}

        results, _, _ = await _search(mutual, gender="female", city_village="Lockpeta")
        assert results[p_her["id"]]["photo_locked"] is False
        assert results[p_her["id"]]["profile_photo"] == {"url": f"/{her_photo}"}
    finally:
        for c in (her, plain, stranger, mutual):
            await c.aclose()


@pytest.mark.asyncio
async def test_photo_lock_only_for_members_who_have_photos():
    """Regression: every blurred member came back photo_locked, so cards
    showed "Photo after mutual interest" for members with no photo at all,
    while their profile page (which counts locked photos) showed none."""
    viewer = await make_client("+919720000010")
    no_photo = await make_client("+919720000011")
    pending_only = await make_client("+919720000012")
    with_photo = await make_client("+919720000013")
    try:
        await create_profile(viewer, display_name="Viewer Vamsi", gender="male")
        p_none = await create_profile(no_photo, display_name="Nophoto Neelima", gender="female",
                                      city_village="Nophotopeta")
        p_pending = await create_profile(pending_only, display_name="Pending Pavani", gender="female",
                                         city_village="Nophotopeta")
        p_with = await create_profile(with_photo, display_name="Photo Priya", gender="female",
                                      city_village="Nophotopeta")
        for p in (p_none, p_pending, p_with):
            assert p["photo_blur_until_mutual"] is True  # women-first default
        await _add_photo(p_pending["id"], approved=None)  # awaiting moderation
        await _add_photo(p_with["id"], is_primary=True)
        resp = await viewer.put("/api/matches/preferences", json={"min_age": 18, "max_age": 99})
        assert resp.status_code == 200, resp.text

        results, _, _ = await _search(viewer, gender="female", city_village="Nophotopeta")
        resp = await viewer.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        recs = {r["profile"]["id"]: r["profile"] for r in resp.json()}
        for cards in (results, recs):
            assert cards[p_none["id"]]["photo_locked"] is False
            assert cards[p_pending["id"]]["photo_locked"] is False
            assert cards[p_with["id"]]["photo_locked"] is True
            assert all(cards[p["id"]]["profile_photo"] is None for p in (p_none, p_pending, p_with))

        # Same answer as the profile page's source: no photos, nothing locked
        for p, expected in ((p_none, []), (p_pending, []), (p_with, [True])):
            resp = await viewer.get(f"/api/profiles/{p['id']}/photos")
            assert resp.status_code == 200, resp.text
            assert [photo["locked"] for photo in resp.json()] == expected
    finally:
        for c in (viewer, no_photo, pending_only, with_photo):
            await c.aclose()


@pytest.mark.asyncio
async def test_search_total_counts_only_profiles_the_viewer_may_see():
    """Regression: verified-only members were dropped after paging, so an
    unverified viewer's total counted them (revealing they exist) and pages
    came back short."""
    unverified = await make_client("+919720000020")
    verified = await make_client("+919720000021")
    public = await make_client("+919720000022")
    vo = await make_client("+919720000023")
    hidden = await make_client("+919720000024")
    try:
        await create_profile(unverified, display_name="Unverified Uday", gender="male")
        await create_profile(verified, display_name="Verified Vikram", gender="male")
        await _set_verified("+919720000021")
        p_public = await create_profile(public, display_name="Public Pooja", gender="female",
                                        city_village="Totalpeta")
        p_vo = await create_profile(vo, display_name="Verified-only Varsha", gender="female",
                                    city_village="Totalpeta", verified_only_opt_in=True)
        p_hidden = await create_profile(hidden, display_name="Hidden Harika", gender="female",
                                        city_village="Totalpeta")
        resp = await hidden.patch("/api/profiles/me/privacy", json={"visibility": "hidden"})
        assert resp.status_code == 200, resp.text

        results, total, text = await _search(unverified, gender="female", city_village="Totalpeta")
        assert results.keys() == {p_public["id"]} and total == 1
        assert "Verified-only Varsha" not in text
        # A one-per-page search is never an empty page with a non-zero total
        for page in (1, 2):
            resp = await unverified.post("/api/search", json={
                "min_age": 18, "max_age": 99, "gender": "female", "city_village": "Totalpeta",
                "limit": 1, "page": page,
            })
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["total"] == 1
            assert [p["id"] for p in body["results"]] == ([p_public["id"]] if page == 1 else [])

        results, total, _ = await _search(verified, gender="female", city_village="Totalpeta")
        assert results.keys() == {p_public["id"], p_vo["id"]} and total == 2
        assert p_hidden["id"] not in results
    finally:
        for c in (unverified, verified, public, vo, hidden):
            await c.aclose()


@pytest.mark.asyncio
async def test_underage_viewer_sees_no_one_even_after_cleanup_or_accepted_interest():
    """Regression: only the profile being viewed was age-checked, never the
    viewer. A legacy minor could search, open adults' profiles and get their
    photo URLs, also after the cleanup (which deactivates and hides only the
    minor's OWN profile), and an interest accepted before the age check kept
    unlocking a blurred member's photos for them."""
    cleanup = _load_cleanup_script()
    blurred = await make_client("+919720000030")  # accepted the minor's interest long ago
    open_f = await make_client("+919720000031")   # shows photos to everyone
    try:
        p_blurred = await create_profile(blurred, display_name="Blurred Bhanu", gender="female",
                                         city_village="Minorpeta")
        p_open = await create_profile(open_f, display_name="Open Oviya", gender="female",
                                      city_village="Minorpeta")
        resp = await open_f.patch("/api/profiles/me/privacy", json={"photo_blur_until_mutual": False})
        assert resp.status_code == 200, resp.text
        blurred_photo = await _add_photo(p_blurred["id"], is_primary=True)
        open_photo = await _add_photo(p_open["id"], is_primary=True)
        blurred_chart = await _add_horoscope(p_blurred["id"])
        minor_id = await _insert_legacy_profile("+919720000032", "Legacy Minor Mohan", Gender.male,
                                                years_ago(17))
        accepted = await _insert_interest(minor_id, p_blurred["id"], InterestStatus.accepted)
        minor = await make_client("+919720000032")

        async def assert_sees_no_one() -> None:
            texts = []
            for pid in (p_blurred["id"], p_open["id"]):
                for path in (f"/api/profiles/{pid}", f"/api/profiles/{pid}/photos",
                             f"/api/horoscope/profile/{pid}"):
                    resp = await minor.get(path)
                    assert resp.status_code == 403, (path, resp.text)
                    texts.append(resp.text)
            results, total, text = await _search(minor, gender="female", city_village="Minorpeta")
            assert results == {} and total == 0
            texts.append(text)
            resp = await minor.get("/api/matches/recommendations?limit=200")
            assert resp.status_code == 200 and resp.json() == [], resp.text
            for kind in ("sent", "received"):
                resp = await minor.get(f"/api/interests/{kind}")
                assert resp.status_code == 200 and resp.json() == [], resp.text
            for secret in (blurred_photo, open_photo, blurred_chart):
                assert not any(secret in t for t in texts)
            async with async_session() as session:
                viewer = await session.scalar(select(User).where(User.phone == "+919720000032"))
                profiles = [await session.get(Profile, pid) for pid in (p_blurred["id"], p_open["id"], minor_id)]
                assert await photo_viewable_profile_ids(session, viewer, profiles) == {minor_id}

        try:
            await assert_sees_no_one()  # before the cleanup has run...
            async with async_session() as session:
                report = await cleanup.deactivate_underage_profiles(session, apply=True)
            assert minor_id in {p.id for p in report.profiles}
            assert await _profile_state(minor_id) == (False, Visibility.hidden)
            await assert_sees_no_one()  # ...and after it
            # The old accepted interest stays on record, it just unlocks nothing
            assert await _interest_status(accepted) == InterestStatus.accepted.value
        finally:
            await minor.aclose()

        # Control: the same endpoints answer an adult member
        resp = await blurred.get(f"/api/profiles/{p_open['id']}/photos")
        assert resp.status_code == 200, resp.text
        assert [p["storage_key"] for p in resp.json()] == [open_photo]
    finally:
        await blurred.aclose()
        await open_f.aclose()


async def _profile_state(profile_id: int) -> tuple[bool, Visibility]:
    async with async_session() as session:
        profile = await session.get(Profile, profile_id)
        return profile.is_active, profile.visibility


@pytest.mark.asyncio
async def test_underage_cleanup_dry_run_then_apply_is_idempotent():
    """Must stay the LAST test in this file: it applies the cleanup to every
    under-age row in the test database, including ones earlier tests left."""
    cleanup = _load_cleanup_script()
    minor_f = await _insert_legacy_profile("+919700000050", "Cleanup Minor", Gender.female,
                                           years_ago(15))
    minor_m = await _insert_legacy_profile("+919700000051", "Cleanup Young", Gender.male,
                                           years_ago(19))
    adult_f = await _insert_legacy_profile("+919700000052", "Cleanup Adult", Gender.female,
                                           years_ago(18))
    adult_m = await _insert_legacy_profile("+919700000053", "Cleanup Man", Gender.male,
                                           years_ago(21))
    minor_f_uid, minor_m_uid, adult_f_uid, adult_m_uid = [
        await _user_id(phone)
        for phone in ("+919700000050", "+919700000051", "+919700000052", "+919700000053")
    ]

    # Rows left from before the age check: rooms and interests with the minors...
    minor_rooms = [
        await _insert_chat_room(minor_f_uid, adult_m_uid, message_from=minor_f_uid),
        await _insert_chat_room(adult_f_uid, minor_m_uid),
    ]
    minor_pending = [
        await _insert_interest(minor_f, adult_m),  # sent by a minor
        await _insert_interest(adult_f, minor_m),  # received by a minor
    ]
    minor_accepted = await _insert_interest(adult_m, minor_f, InterestStatus.accepted)
    # ...and between adults, which the cleanup must not touch
    adults_room = await _insert_chat_room(adult_m_uid, adult_f_uid)
    adults_pending = await _insert_interest(adult_f, adult_m)

    async def assert_untouched_controls() -> None:
        assert await _room_is_active(adults_room)
        assert await _interest_status(adults_pending) == InterestStatus.pending.value
        # Only pending interests are cancelled (the accepted one's room is closed)
        assert await _interest_status(minor_accepted) == InterestStatus.accepted.value

    async with async_session() as session:
        report = await cleanup.deactivate_underage_profiles(session)  # dry run
    found = {p.id: p for p in report.profiles}
    assert report.updated == 0
    assert minor_f in found and minor_m in found
    assert adult_f not in found and adult_m not in found
    assert found[minor_f].age == 15 and found[minor_f].gender == "female"
    assert found[minor_m].age == 19 and found[minor_m].gender == "male"
    assert found[minor_f].needs_update and found[minor_m].needs_update
    assert report.open_chat_rooms >= 2 and report.pending_interests >= 2
    assert report.chat_rooms_closed == 0 and report.interests_cancelled == 0
    for pid in (minor_f, minor_m):
        assert await _profile_state(pid) == (True, Visibility.public)  # nothing written
    for room_id in minor_rooms:
        assert await _room_is_active(room_id)
    for interest_id in minor_pending:
        assert await _interest_status(interest_id) == InterestStatus.pending.value
    await assert_untouched_controls()

    async with async_session() as session:
        report = await cleanup.deactivate_underage_profiles(session, apply=True)
    assert report.updated >= 2
    assert report.chat_rooms_closed == report.open_chat_rooms >= 2
    assert report.interests_cancelled == report.pending_interests >= 2
    for pid in (minor_f, minor_m):
        assert await _profile_state(pid) == (False, Visibility.hidden)
    for pid in (adult_f, adult_m):
        assert await _profile_state(pid) == (True, Visibility.public)
    for room_id in minor_rooms:
        assert not await _room_is_active(room_id)
    for interest_id in minor_pending:
        assert await _interest_status(interest_id) == InterestStatus.cancelled.value
    await assert_untouched_controls()

    async with async_session() as session:
        report = await cleanup.deactivate_underage_profiles(session, apply=True)
    assert report.updated == 0
    assert not any(p.needs_update for p in report.profiles)
    assert report.open_chat_rooms == 0 and report.pending_interests == 0
    assert report.chat_rooms_closed == 0 and report.interests_cancelled == 0
    await assert_untouched_controls()
    async with async_session() as session:  # rows are kept, never deleted
        assert await session.get(Profile, minor_f) is not None
        assert await session.get(ChatRoom, minor_rooms[0]) is not None
        assert await session.get(Interest, minor_pending[0]) is not None
