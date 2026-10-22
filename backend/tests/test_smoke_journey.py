"""
End-to-end smoke test: walks every endpoint the frontend calls, in the order
a real user would hit them. Guards against response-serialization 500s that
per-feature tests miss (ORM → schema mismatches, missing fields, etc.).
"""

import pytest
from sqlalchemy import update

from tests.conftest import make_client, create_profile
from app.database import async_session
from app.models.user import User, UserRole

# Minimal bytes that pass the content-type gate (magic bytes not checked)
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.mark.asyncio
async def test_full_user_journey():
    ravi = await make_client("+919300000001")    # male seeker
    priya = await make_client("+919300000002")   # female seeker
    admin = await make_client("+919300000003")
    try:
        async with async_session() as session:
            await session.execute(
                update(User).where(User.phone == "+919300000003").values(role=UserRole.admin)
            )
            await session.commit()

        # ── Onboarding ──────────────────────────────────────
        p_ravi = await create_profile(ravi, display_name="Ravi Smoke", gender="male", height_cm=175)
        p_priya = await create_profile(priya, display_name="Priya Smoke", gender="female")

        # ── Taxonomy (register/search dropdowns) ────────────
        for path in ("/api/taxonomy/religions", "/api/taxonomy/regions",
                     "/api/taxonomy/language-groups", "/api/taxonomy/communities"):
            resp = await ravi.get(path)
            assert resp.status_code == 200, f"{path}: {resp.text}"

        # ── Profile edit + privacy ──────────────────────────
        resp = await ravi.patch("/api/profiles/me", json={"bio": "Smoke test bio", "education_level": "B.Tech"})
        assert resp.status_code == 200, resp.text
        resp = await ravi.patch("/api/profiles/me/privacy", json={"photo_blur_until_mutual": False})
        assert resp.status_code == 200, resp.text
        resp = await ravi.get("/api/profiles/me")
        assert resp.status_code == 200

        # ── Horoscope ───────────────────────────────────────
        resp = await ravi.put("/api/horoscope/me", json={
            "rasi": "Mesha (Aries)", "star": "Ashwini", "dosham": False,
            "time_of_birth": "10:30 AM", "place_of_birth": "Hyderabad",
        })
        assert resp.status_code == 200, resp.text
        resp = await ravi.get("/api/horoscope/me")
        assert resp.status_code == 200
        resp = await ravi.post("/api/horoscope/me/chart",
                               files={"file": ("chart.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 200, resp.text
        assert resp.json()["chart_images"][0].startswith("/uploads/horoscopes/")

        # ── Photos ──────────────────────────────────────────
        resp = await ravi.post("/api/profiles/me/photos",
                               files={"file": ("me.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 201, resp.text
        photo_id = resp.json()["id"]
        resp = await ravi.get("/api/profiles/me/photos")
        assert resp.status_code == 200 and len(resp.json()) == 1

        # ── Search + matches ────────────────────────────────
        resp = await ravi.post("/api/search", json={"min_age": 18, "max_age": 45, "gender": "female"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] >= 1
        # limit=200: equal scores tie, so the default top 20 depends on how many
        # other members earlier tests left in the shared test database
        resp = await ravi.get("/api/matches/recommendations?limit=200")
        assert resp.status_code == 200, resp.text
        recs = resp.json()
        assert any(r["profile"]["id"] == p_priya["id"] for r in recs)
        assert all("confidence" in r for r in recs)
        resp = await ravi.get("/api/matches/preferences")
        assert resp.status_code == 200
        resp = await ravi.put("/api/matches/preferences", json={"min_age": 21, "max_age": 32})
        assert resp.status_code == 200, resp.text

        # ── Public profile views ────────────────────────────
        resp = await ravi.get(f"/api/profiles/{p_priya['id']}")
        assert resp.status_code == 200, resp.text
        resp = await ravi.get(f"/api/profiles/{p_priya['id']}/photos")
        assert resp.status_code == 200
        resp = await priya.get(f"/api/horoscope/profile/{p_ravi['id']}")
        assert resp.status_code == 200, resp.text

        # ── Interests → mutual → chat ───────────────────────
        resp = await ravi.post(f"/api/interests/{p_priya['id']}")
        assert resp.status_code == 200, resp.text
        resp = await priya.get("/api/interests/received")
        assert resp.status_code == 200, resp.text
        received = resp.json()
        assert len(received) == 1 and received[0]["sender"]["display_name"] == "Ravi Smoke"
        interest_id = received[0]["id"]
        resp = await ravi.get("/api/interests/sent")
        assert resp.status_code == 200 and len(resp.json()) == 1

        resp = await priya.put(f"/api/interests/{interest_id}/accept")
        assert resp.status_code == 200, resp.text

        resp = await ravi.get("/api/chat/rooms")
        assert resp.status_code == 200, resp.text
        rooms = resp.json()
        assert len(rooms) == 1
        room_id = rooms[0]["id"]
        other_names = [
            part["user"]["profile"]["display_name"]
            for part in rooms[0]["participants"] if part["user"] and part["user"]["profile"]
        ]
        assert "Priya Smoke" in other_names

        resp = await ravi.post(f"/api/chat/rooms/{room_id}/messages",
                               json={"content": "Namaste! Nice to match with you."})
        assert resp.status_code == 200, resp.text
        resp = await priya.get(f"/api/chat/rooms/{room_id}/messages")
        assert resp.status_code == 200 and len(resp.json()) == 1
        # Contact-sharing moderation still enforced
        resp = await ravi.post(f"/api/chat/rooms/{room_id}/messages",
                               json={"content": "call me 9876543210"})
        assert resp.status_code == 403
        # Inbox preview present
        resp = await priya.get("/api/chat/rooms")
        assert resp.json()[0]["latest_message"]["content"].startswith("Namaste")

        # ── Notifications ───────────────────────────────────
        resp = await priya.get("/api/notifications?limit=5")
        assert resp.status_code == 200, resp.text
        notifs = resp.json()
        assert len(notifs) >= 1
        resp = await priya.patch(f"/api/notifications/{notifs[0]['id']}/read")
        assert resp.status_code == 200
        resp = await priya.patch("/api/notifications/read-all")
        assert resp.status_code == 200

        # ── Payments ────────────────────────────────────────
        resp = await ravi.get("/api/payments/plans")
        assert resp.status_code == 200, resp.text
        plan_id = resp.json()[0]["id"]
        resp = await ravi.post("/api/payments/trial")
        assert resp.status_code == 200, resp.text
        resp = await ravi.get("/api/payments/my-subscription")
        assert resp.status_code == 200 and resp.json()["is_active"] is True
        # Paid checkout (mock provider)
        resp = await priya.post("/api/payments/create-order", json={"plan_id": plan_id})
        assert resp.status_code == 200, resp.text
        order_id = resp.json()["order_id"]
        resp = await priya.post("/api/payments/mock/sign",
                                json={"order_id": order_id, "payment_id": "pay_smoke_1"})
        assert resp.status_code == 200
        signature = resp.json()["signature"]
        resp = await priya.post("/api/payments/verify", json={
            "order_id": order_id, "payment_id": "pay_smoke_1", "signature": signature,
        })
        assert resp.status_code == 200, resp.text

        # ── Expert services ─────────────────────────────────
        resp = await ravi.post("/api/expert/inquiry", json={
            "category": "matchmaking", "message": "Help me find a match",
            "preferred_contact_time": "Evenings",
        })
        assert resp.status_code == 200, resp.text
        resp = await ravi.get("/api/expert/inquiries")
        assert resp.status_code == 200 and len(resp.json()) == 1

        # ── Reports + panic block ───────────────────────────
        resp = await priya.post("/api/reports", json={
            "target_profile_id": p_ravi["id"], "reason": "other", "evidence_text": "smoke",
        })
        assert resp.status_code == 201, resp.text
        resp = await priya.post(f"/api/safety/block/{p_ravi['id']}", json={})
        assert resp.status_code == 201, resp.text
        resp = await priya.get("/api/safety/blocks")
        assert resp.status_code == 200 and len(resp.json()) == 1
        resp = await ravi.get(f"/api/profiles/{p_priya['id']}")
        assert resp.status_code == 403  # blocked
        resp = await priya.delete(f"/api/safety/block/{p_ravi['id']}")
        assert resp.status_code == 200

        # ── Settings (contact + digest consent) ─────────────
        resp = await ravi.patch("/api/auth/me/contact", json={
            "email": "ravi.smoke@example.com", "email_digest_opt_in": True,
        })
        assert resp.status_code == 200, resp.text

        # ── Admin surface ───────────────────────────────────
        for path in ("/api/admin/stats", "/api/admin/users", "/api/admin/photos/pending",
                     "/api/admin/reports", "/api/admin/taxonomy/suggestions",
                     "/api/expert/admin/all", "/api/expert/admin/sessions"):
            resp = await admin.get(path)
            assert resp.status_code == 200, f"{path}: {resp.text}"
        resp = await admin.patch(f"/api/admin/photos/{photo_id}/approve")
        assert resp.status_code == 200, resp.text
        resp = await admin.post("/api/admin/digest/send")
        assert resp.status_code == 200, resp.text
        assert resp.json()["eligible_users"] >= 1  # ravi opted in (email disabled → skipped)
        resp = await admin.post("/api/expert/admin/sessions/send-reminders")
        assert resp.status_code == 200

        # Approved photo now publicly visible
        resp = await priya.get(f"/api/profiles/{p_ravi['id']}/photos")
        assert resp.status_code == 200 and len(resp.json()) == 1

        # ── Logout ──────────────────────────────────────────
        resp = await ravi.post("/api/auth/logout")
        assert resp.status_code == 200
    finally:
        await ravi.aclose()
        await priya.aclose()
        await admin.aclose()
