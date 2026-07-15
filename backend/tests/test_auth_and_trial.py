"""Auth flow, trial-once enforcement (Epic H1), digest consent."""

import pytest

from tests.conftest import login, make_client


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_otp_login_sets_cookies_and_me(client):
    data = await login(client, "+919000000001")
    assert data["is_new_user"] is True
    assert client.cookies.get("access_token")

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["phone"] == "+919000000001"


@pytest.mark.asyncio
async def test_otp_dev_echo_flag(client, monkeypatch):
    from app.config import settings

    # Off by default: response must NOT leak the OTP
    resp = await client.post("/api/auth/otp/request", json={"phone": "+919000000010"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["dev_otp"] is None

    # Enabled: OTP is echoed for dev/staging testing (frontend shows a toast)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    resp = await client.post("/api/auth/otp/request", json={"phone": "+919000000011"})
    assert resp.status_code == 200, resp.text
    dev_otp = resp.json()["dev_otp"]
    assert dev_otp and len(dev_otp) == 6 and dev_otp.isdigit()

    # And the echoed OTP actually verifies
    resp = await client.post("/api/auth/otp/verify",
                             json={"phone": "+919000000011", "otp": dev_otp})
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_trial_only_once_per_phone(client):
    await login(client, "+919000000002")

    first = await client.post("/api/payments/trial")
    assert first.status_code == 200, first.text

    second = await client.post("/api/payments/trial")
    assert second.status_code == 400
    assert "already used" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_digest_requires_email(client):
    await login(client, "+919000000003")

    # Opt-in without email → rejected
    resp = await client.patch("/api/auth/me/contact", json={"email_digest_opt_in": True})
    assert resp.status_code == 400

    # Email + opt-in → accepted and reflected in /me
    resp = await client.patch(
        "/api/auth/me/contact",
        json={"email": "digest-user@example.com", "email_digest_opt_in": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "digest-user@example.com"
    assert body["email_digest_opt_in"] is True
