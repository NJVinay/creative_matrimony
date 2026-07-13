"""Expert sessions — tier gating (Epic I1) and Personal Care (Epic I2)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from tests.conftest import make_client
from app.database import async_session
from app.models.user import User, UserRole


def _future(days: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.mark.asyncio
async def test_free_tier_session_quota_and_duration():
    member = await make_client("+919200000001")
    try:
        # 60 min exceeds the free-tier cap
        resp = await member.post("/api/expert/sessions", json={
            "scheduled_at": _future(), "duration_minutes": 60,
        })
        assert resp.status_code == 400

        # First 30-min session is allowed
        resp = await member.post("/api/expert/sessions", json={
            "scheduled_at": _future(), "duration_minutes": 30,
        })
        assert resp.status_code == 201, resp.text
        session_id = resp.json()["id"]

        # Second session in the same month exceeds the free quota
        resp = await member.post("/api/expert/sessions", json={
            "scheduled_at": _future(4), "duration_minutes": 30,
        })
        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()

        # Member can cancel their own session
        resp = await member.patch(f"/api/expert/sessions/{session_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
    finally:
        await member.aclose()


@pytest.mark.asyncio
async def test_paid_tier_gets_bigger_quota():
    member = await make_client("+919200000002")
    try:
        # Trial activates a subscription → paid limits apply
        resp = await member.post("/api/payments/trial")
        assert resp.status_code == 200, resp.text

        resp = await member.post("/api/expert/sessions", json={
            "scheduled_at": _future(), "duration_minutes": 60,
        })
        assert resp.status_code == 201, resp.text
    finally:
        await member.aclose()


@pytest.mark.asyncio
async def test_personal_care_flow():
    member = await make_client("+919200000003")
    admin = await make_client("+919200000004")
    try:
        async with async_session() as session:
            await session.execute(
                update(User).where(User.phone == "+919200000004").values(role=UserRole.admin)
            )
            await session.commit()

        member_id = (await member.get("/api/auth/me")).json()["id"]
        admin_id = (await admin.get("/api/auth/me")).json()["id"]

        # Admin assigns themselves as the expert (admin counts as expert role)
        resp = await admin.post("/api/expert/admin/care", json={
            "user_id": member_id,
            "expert_user_id": admin_id,
            "service_fee": 4999,
            "notes": "Personal care engagement",
        })
        assert resp.status_code == 201, resp.text
        assignment_id = resp.json()["id"]

        # Checklist task + call log
        resp = await admin.post(f"/api/expert/admin/care/{assignment_id}/tasks",
                                json={"title": "Shortlist 5 profiles"})
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        resp = await admin.patch(f"/api/expert/admin/care/tasks/{task_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["is_done"] is True

        resp = await admin.post(f"/api/expert/admin/care/{assignment_id}/calls",
                                json={"duration_minutes": 15, "summary": "Intro call"})
        assert resp.status_code == 201

        # Member sees the engagement with task + call
        resp = await member.get("/api/expert/care/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["service_fee"] == 4999
        assert len(body["tasks"]) == 1
        assert len(body["call_logs"]) == 1

        # Close it
        resp = await admin.patch(f"/api/expert/admin/care/{assignment_id}/close")
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
    finally:
        await member.aclose()
        await admin.aclose()
