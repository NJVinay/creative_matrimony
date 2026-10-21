"""Admin moderation queues must point at the right member (profile id, not user id)."""

import pytest
from sqlalchemy import update

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_reports_and_inquiries_expose_profile_ids_and_names():
    admin = await make_client("+919600000001")   # has no profile → user/profile ids diverge
    reporter = await make_client("+919600000002")
    target = await make_client("+919600000003")
    try:
        async with async_session() as session:
            await session.execute(
                update(User).where(User.phone == "+919600000001").values(role=UserRole.admin)
            )
            await session.commit()

        p_reporter = await create_profile(reporter, display_name="Reporter Rani", gender="female")
        p_target = await create_profile(target, display_name="Target Teja", gender="male")
        target_user_id = (await target.get("/api/auth/me")).json()["id"]
        assert target_user_id != p_target["id"]  # the mix-up this guards against

        resp = await reporter.post("/api/reports", json={
            "target_profile_id": p_target["id"], "reason": "harassment",
        })
        assert resp.status_code == 201, resp.text
        report_id = resp.json()["id"]

        resp = await admin.get("/api/admin/reports")
        assert resp.status_code == 200, resp.text
        row = next(r for r in resp.json() if r["id"] == report_id)
        assert row["target_user_id"] == target_user_id
        assert row["target_profile_id"] == p_target["id"]
        assert row["target_name"] == "Target Teja"
        assert row["reporter_profile_id"] == p_reporter["id"]
        assert row["reporter_name"] == "Reporter Rani"

        resp = await admin.patch(f"/api/admin/reports/{report_id}/resolve")
        assert resp.status_code == 200, resp.text
        assert resp.json()["target_profile_id"] == p_target["id"]

        resp = await target.post("/api/expert/inquiry", json={
            "category": "astrology", "message": "Need a horoscope match",
        })
        assert resp.status_code == 200, resp.text
        inquiry_id = resp.json()["id"]

        resp = await admin.get("/api/expert/admin/all")
        assert resp.status_code == 200, resp.text
        row = next(i for i in resp.json() if i["id"] == inquiry_id)
        assert row["user_id"] == target_user_id
        assert row["profile_id"] == p_target["id"]
        assert row["display_name"] == "Target Teja"
    finally:
        await admin.aclose()
        await reporter.aclose()
        await target.aclose()
