"""OTP delivery providers — Fast2SMS and WhatsApp Cloud API (httpx mocked)."""

import pytest

import app.services.otp_service as otp_service
from app.services.otp_service import (
    OTPDeliveryError, send_otp, _whatsapp_number, _fast2sms_number,
)
from app.config import settings


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text or str(body)

    def json(self):
        return self._body


class FakeAsyncClient:
    """Captures the outbound request instead of hitting the network."""
    last_call = None
    next_response = FakeResponse()

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        FakeAsyncClient.last_call = {"url": url, **kwargs}
        return FakeAsyncClient.next_response


@pytest.fixture
def fake_http(monkeypatch):
    monkeypatch.setattr(otp_service.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.last_call = None
    FakeAsyncClient.next_response = FakeResponse()
    return FakeAsyncClient


def test_phone_normalization():
    # WhatsApp: E.164 digits, bare 10-digit assumed Indian
    assert _whatsapp_number("+919876543210") == "919876543210"
    assert _whatsapp_number("9876543210") == "919876543210"
    assert _whatsapp_number("+46701234567") == "46701234567"
    # Fast2SMS: 10-digit subscriber number
    assert _fast2sms_number("+919876543210") == "9876543210"
    assert _fast2sms_number("9876543210") == "9876543210"


@pytest.mark.asyncio
async def test_fast2sms_success(fake_http, monkeypatch):
    monkeypatch.setattr(settings, "OTP_PROVIDER", "fast2sms")
    monkeypatch.setattr(settings, "FAST2SMS_API_KEY", "test-key")
    fake_http.next_response = FakeResponse(200, {"return": True})

    await send_otp("+919876543210", "482913")

    call = fake_http.last_call
    assert "fast2sms.com" in call["url"]
    assert call["headers"]["authorization"] == "test-key"
    assert call["data"] == {"route": "otp", "variables_values": "482913", "numbers": "9876543210"}


@pytest.mark.asyncio
async def test_fast2sms_rejects_non_indian_numbers(fake_http, monkeypatch):
    monkeypatch.setattr(settings, "OTP_PROVIDER", "fast2sms")
    monkeypatch.setattr(settings, "FAST2SMS_API_KEY", "test-key")

    with pytest.raises(OTPDeliveryError, match="Indian numbers"):
        await send_otp("+46701234567", "482913")


@pytest.mark.asyncio
async def test_fast2sms_failure_raises(fake_http, monkeypatch):
    monkeypatch.setattr(settings, "OTP_PROVIDER", "fast2sms")
    monkeypatch.setattr(settings, "FAST2SMS_API_KEY", "bad-key")
    fake_http.next_response = FakeResponse(401, {"return": False}, "invalid auth")

    with pytest.raises(OTPDeliveryError):
        await send_otp("+919876543210", "482913")


@pytest.mark.asyncio
async def test_whatsapp_success_sends_auth_template(fake_http, monkeypatch):
    monkeypatch.setattr(settings, "OTP_PROVIDER", "whatsapp")
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "test-token")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "1234567890")
    fake_http.next_response = FakeResponse(200, {"messages": [{"id": "wamid.X"}]})

    await send_otp("9876543210", "482913")

    call = fake_http.last_call
    assert call["url"] == "https://graph.facebook.com/v20.0/1234567890/messages"
    assert call["headers"]["Authorization"] == "Bearer test-token"
    payload = call["json"]
    assert payload["to"] == "919876543210"
    assert payload["template"]["name"] == settings.WHATSAPP_TEMPLATE_NAME
    # Auth templates need the OTP in BOTH body and copy-code button
    body_comp, button_comp = payload["template"]["components"]
    assert body_comp["parameters"][0]["text"] == "482913"
    assert button_comp["sub_type"] == "url"
    assert button_comp["parameters"][0]["text"] == "482913"


@pytest.mark.asyncio
async def test_whatsapp_failure_raises(fake_http, monkeypatch):
    monkeypatch.setattr(settings, "OTP_PROVIDER", "whatsapp")
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "expired-token")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "1234567890")
    fake_http.next_response = FakeResponse(401, {"error": {"message": "token expired"}})

    with pytest.raises(OTPDeliveryError):
        await send_otp("+919876543210", "482913")


@pytest.mark.asyncio
async def test_unconfigured_provider_raises(monkeypatch):
    monkeypatch.setattr(settings, "OTP_PROVIDER", "whatsapp")
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "")
    with pytest.raises(OTPDeliveryError, match="not configured"):
        await send_otp("+919876543210", "482913")


@pytest.mark.asyncio
async def test_delivery_failure_returns_502_and_no_cooldown(client, monkeypatch):
    """A failed send must return 502 and roll back, so an immediate retry
    is not blocked by the per-phone cooldown."""
    monkeypatch.setattr(settings, "OTP_PROVIDER", "fast2sms")
    monkeypatch.setattr(settings, "FAST2SMS_API_KEY", "")  # unconfigured → delivery error

    resp = await client.post("/api/auth/otp/request", json={"phone": "+919000000020"})
    assert resp.status_code == 502

    # Retry with a working provider: no cooldown block from the failed attempt
    monkeypatch.setattr(settings, "OTP_PROVIDER", "mock")
    resp = await client.post("/api/auth/otp/request", json={"phone": "+919000000020"})
    assert resp.status_code == 200, resp.text
