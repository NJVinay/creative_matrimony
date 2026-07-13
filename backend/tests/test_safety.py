"""Panic block (safety), ban evasion (Epic J2), women-first defaults."""

import pytest
from sqlalchemy import select, update

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.user import User, UserRole
from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_panic_block_hides_profile_and_stops_interests():
    alice = await make_client("+919100000001")
    bob = await make_client("+919100000002")
    try:
        alice_profile = await create_profile(alice, display_name="Alice Test", gender="female")
        bob_profile = await create_profile(bob, display_name="Bob Test", gender="male")

        # Bob can see Alice before the block
        resp = await bob.get(f"/api/profiles/{alice_profile['id']}")
        assert resp.status_code == 200

        # Alice panic-blocks Bob
        resp = await alice.post(f"/api/safety/block/{bob_profile['id']}", json={"reason": "test"})
        assert resp.status_code == 201, resp.text

        # Bob can no longer view Alice, in either direction
        resp = await bob.get(f"/api/profiles/{alice_profile['id']}")
        assert resp.status_code == 403
        resp = await alice.get(f"/api/profiles/{bob_profile['id']}")
        assert resp.status_code == 403

        # Bob cannot send an interest to Alice
        resp = await bob.post(f"/api/interests/{alice_profile['id']}")
        assert resp.status_code == 400

        # Unblock restores visibility
        resp = await alice.delete(f"/api/safety/block/{bob_profile['id']}")
        assert resp.status_code == 200
        resp = await bob.get(f"/api/profiles/{alice_profile['id']}")
        assert resp.status_code == 200
    finally:
        await alice.aclose()
        await bob.aclose()


@pytest.mark.asyncio
async def test_ban_blocks_reentry_and_flags_evasion():
    target_phone = "+919100000003"
    target = await make_client(target_phone)
    admin = await make_client("+919100000004")
    try:
        # Promote the second user to admin directly in the DB
        async with async_session() as session:
            await session.execute(
                update(User).where(User.phone == "+919100000004").values(role=UserRole.admin)
            )
            await session.commit()

        target_id = (await target.get("/api/auth/me")).json()["id"]

        resp = await admin.patch(f"/api/admin/users/{target_id}/ban", json={"reason": "test ban"})
        assert resp.status_code == 200, resp.text

        # Banned phone cannot request a new OTP (re-entry blocked)
        resp = await target.post("/api/auth/otp/request", json={"phone": target_phone})
        assert resp.status_code == 403

        # The evasion attempt is audit-flagged
        async with async_session() as session:
            flag = await session.scalar(
                select(AuditLog).where(AuditLog.action == "ban_evasion_attempt")
            )
            assert flag is not None

        # Unban lifts the blocklist
        resp = await admin.patch(f"/api/admin/users/{target_id}/unban")
        assert resp.status_code == 200
    finally:
        await target.aclose()
        await admin.aclose()


@pytest.mark.asyncio
async def test_women_first_privacy_defaults():
    her = await make_client("+919100000005")
    him = await make_client("+919100000006")
    try:
        p_her = await create_profile(
            her, display_name="Devi Test", gender="female", verified_only_opt_in=True
        )
        assert p_her["photo_blur_until_mutual"] is True
        assert p_her["visibility"] == "verified_only"

        p_him = await create_profile(him, display_name="Ravi Test", gender="male")
        assert p_him["photo_blur_until_mutual"] is False
        assert p_him["visibility"] == "public"
    finally:
        await her.aclose()
        await him.aclose()
