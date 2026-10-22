"""OTP throttling. Codes are bound to the browser that requested them (its
otp_device cookie): only that browser can check one. Per phone there is a
resend window per device (OTP_RESEND_SECONDS), a cap on codes for devices that
have never logged in to the phone (OTP_MAX_SENDS_PER_HOUR), and a per-code
attempt budget (OTP_MAX_ATTEMPTS). So strangers can neither use up the owner's
code nor stop the owner's browser getting one, guessing per phone stays
bounded, and the limits hold however many requests run at once."""

import asyncio
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.database import async_session
from app.main import application
from app.models.user import OTPLog
from app.services.otp_service import OTP_DEVICE_COOKIE


@pytest.fixture
def otp_settings(monkeypatch):
    """Production-like limits (conftest relaxes them for the rest of the suite),
    with the OTP echoed in the response so tests can enter right and wrong codes."""
    monkeypatch.setattr(settings, "OTP_RESEND_SECONDS", 60)
    monkeypatch.setattr(settings, "OTP_MAX_SENDS_PER_HOUR", 5)
    monkeypatch.setattr(settings, "OTP_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)


def _new_client(device_id: str | None = None) -> AsyncClient:
    """A separate browser: own cookie jar, same app. With `device_id`, every
    request carries just that otp_device cookie (another tab of that browser,
    for the OTP endpoints only: the jar's cookies are not sent then)."""
    headers = {"Cookie": f"{OTP_DEVICE_COOKIE}={device_id}"} if device_id else None
    return AsyncClient(transport=ASGITransport(app=application), base_url="https://testserver",
                       headers=headers)


def _device(client: AsyncClient) -> str:
    """The otp_device cookie /otp/request set on this browser."""
    device_id = client.cookies.get(OTP_DEVICE_COOKIE)
    assert device_id, "no otp_device cookie set"
    return device_id


async def _request(client, phone: str):
    return await client.post("/api/auth/otp/request", json={"phone": phone})


async def _verify(client, phone: str, otp: str):
    return await client.post("/api/auth/otp/verify", json={"phone": phone, "otp": otp})


def _wrong(otp: str, n: int = 0) -> str:
    """The n-th 6-digit code that is not `otp`."""
    codes = [f"{i:06d}" for i in range(n + 2)]
    return [c for c in codes if c != otp][n]


async def _travel(phone: str, seconds: int) -> None:
    """Pretend `seconds` have passed for this phone: shift its OTP
    timestamps into the past instead of sleeping."""
    delta = timedelta(seconds=seconds)
    async with async_session() as session:
        for row in (await session.scalars(select(OTPLog).where(OTPLog.phone == phone))).all():
            row.created_at -= delta
            if row.verified_at:
                row.verified_at -= delta
        await session.commit()


async def _attempts(phone: str) -> list[int]:
    """Attempts used on each code sent to the phone, oldest first."""
    async with async_session() as session:
        return list((await session.scalars(
            select(OTPLog.attempts).where(OTPLog.phone == phone).order_by(OTPLog.id)
        )).all())


async def _codes_sent(phone: str) -> int:
    async with async_session() as session:
        return await session.scalar(select(func.count(OTPLog.id)).where(OTPLog.phone == phone))


def _retry_after(resp) -> int:
    return int(resp.headers["retry-after"])


@pytest.mark.asyncio
async def test_request_reports_resend_window(client, otp_settings, monkeypatch):
    monkeypatch.setattr(settings, "OTP_RESEND_SECONDS", 45)
    resp = await _request(client, "+919200000001")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["resend_after_seconds"] == 45
    assert body["expires_in_seconds"] == settings.OTP_EXPIRE_SECONDS
    # The code is bound to this browser through an httpOnly cookie
    cookie = resp.headers["set-cookie"]
    assert f"{OTP_DEVICE_COOKIE}=" in cookie and "HttpOnly" in cookie


@pytest.mark.asyncio
async def test_immediate_rerequest_is_429_with_wait_hint(client, otp_settings):
    phone = "+919200000002"
    assert (await _request(client, phone)).status_code == 200

    resp = await _request(client, phone)
    assert resp.status_code == 429
    wait = _retry_after(resp)
    assert 0 < wait <= 60
    # The message tells the member how long, not just "wait"
    assert f"{wait} second" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_new_request_allowed_after_resend_window(client, otp_settings):
    """Regression: the 600s lockout setting used to block every re-request
    for 10 minutes (e.g. log out, then try to log back in)."""
    phone = "+919200000003"
    assert (await _request(client, phone)).status_code == 200

    await _travel(phone, 61)
    resp = await _request(client, phone)
    assert resp.status_code == 200, resp.text

    # The window restarts from the new code
    assert (await _request(client, phone)).status_code == 429


@pytest.mark.asyncio
async def test_relogin_right_after_logout_is_not_blocked(client, otp_settings):
    """A code that was used to log in does not hold up the next login."""
    phone = "+919200000004"
    otp = (await _request(client, phone)).json()["dev_otp"]
    assert (await _verify(client, phone, otp)).status_code == 200
    assert (await client.post("/api/auth/logout")).status_code == 200

    resp = await _request(client, phone)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_max_wrong_codes_burn_only_that_code(client, otp_settings):
    phone = "+919200000005"
    otp = (await _request(client, phone)).json()["dev_otp"]

    for _ in range(settings.OTP_MAX_ATTEMPTS - 1):
        assert (await _verify(client, phone, _wrong(otp))).status_code == 401
    # The attempt that uses the code up says so, and when a new one can be sent
    resp = await _verify(client, phone, _wrong(otp))
    assert resp.status_code == 429
    wait = _retry_after(resp)
    assert 0 < wait <= 60
    assert "request a new OTP" in resp.json()["detail"]
    assert f"{wait} second" in resp.json()["detail"]

    # That code is dead, even typed right
    assert (await _verify(client, phone, otp)).status_code == 429

    # A new code comes after the resend window (no longer lockout), with its own budget
    assert (await _request(client, phone)).status_code == 429
    await _travel(phone, 61)
    resp = await _request(client, phone)
    assert resp.status_code == 200, resp.text
    fresh = resp.json()["dev_otp"]
    assert (await _verify(client, phone, _wrong(fresh))).status_code == 401
    assert (await _verify(client, phone, fresh)).status_code == 200


@pytest.mark.asyncio
async def test_strangers_cannot_use_up_or_hold_up_the_owners_code(otp_settings):
    """Regression: wrong codes from anyone used to use up the owner's code, and
    a stranger's request started the phone-wide resend window, so the owner
    could neither log in with the code they had nor get a new one."""
    victim = "+919200000006"
    async with _new_client() as owner, _new_client() as attacker:
        sms = (await _request(owner, victim)).json()["dev_otp"]  # what the owner receives

        # Guesses from another browser are never checked against the owner's code,
        # however many: they are refused like a wrong code, and nothing is used up
        for n in range(settings.OTP_MAX_ATTEMPTS + 2):
            assert (await _verify(attacker, victim, _wrong(sms, n))).status_code == 401
        assert (await _verify(attacker, victim, sms)).status_code == 401  # even the right one
        assert await _attempts(victim) == [0]

        # The stranger's own request does not hold up the owner's
        assert (await _request(attacker, victim)).status_code == 200
        assert (await _verify(owner, victim, sms)).status_code == 200


@pytest.mark.asyncio
async def test_stranger_cannot_sustain_a_lockout(otp_settings):
    """Regression (multi-round): in each resend window a stranger requested the
    victim's code first and spent all its attempts. Now, whatever the stranger
    does each round, the owner's own request and login go through."""
    victim = "+919200000010"
    log = []
    async with _new_client() as owner:
        for _ in range(3):
            async with _new_client() as attacker:  # a fresh browser every round
                resp = await _request(attacker, victim)
                assert resp.status_code == 200, resp.text
                code = resp.json()["dev_otp"]
                guesses = [(await _verify(attacker, victim, _wrong(code, n))).status_code
                           for n in range(settings.OTP_MAX_ATTEMPTS)]
                # The stranger only ever uses up their own code
                assert guesses == [401] * (settings.OTP_MAX_ATTEMPTS - 1) + [429]

            req = await _request(owner, victim)
            ver = await _verify(owner, victim, req.json().get("dev_otp") or "")
            log.append((req.status_code, ver.status_code))
            assert (await owner.post("/api/auth/logout")).status_code == 200
            await _travel(victim, 61)
    assert log == [(200, 200)] * 3


@pytest.mark.asyncio
async def test_devices_new_to_a_phone_share_an_hourly_cap(otp_settings):
    """Regression: with a per-phone resend window alone a phone could be sent a
    code a minute, so 3 checked guesses a minute (180/hour) for whoever asked.
    Devices that never logged in to the phone now share OTP_MAX_SENDS_PER_HOUR
    codes an hour; the owner's browser, known to the phone, is exempt."""
    phone = "+919200000011"
    cap = settings.OTP_MAX_SENDS_PER_HOUR
    async with _new_client() as owner:
        # The owner logged in from this browser before
        otp = (await _request(owner, phone)).json()["dev_otp"]
        assert (await _verify(owner, phone, otp)).status_code == 200
        assert (await owner.post("/api/auth/logout")).status_code == 200

        # Strangers with fresh browsers (IPs do not matter) get `cap` codes...
        for _ in range(cap):
            async with _new_client() as attacker:
                resp = await _request(attacker, phone)
                assert resp.status_code == 200, resp.text
                code = resp.json()["dev_otp"]
                for n in range(settings.OTP_MAX_ATTEMPTS + 1):
                    await _verify(attacker, phone, _wrong(code, n))
        # ...and no more this hour
        async with _new_client() as attacker:
            resp = await _request(attacker, phone)
            assert resp.status_code == 429, resp.text
            assert "Too many OTPs were requested for this number" in resp.json()["detail"]
            assert 3500 < _retry_after(resp) <= 3600
            assert "minutes" in resp.json()["detail"]
        # So at most cap x OTP_MAX_ATTEMPTS guesses an hour were checked
        # (the owner's 1 is their login)
        assert await _attempts(phone) == [1] + [settings.OTP_MAX_ATTEMPTS] * cap

        # The cap never locks the owner's known browser out
        resp = await _request(owner, phone)
        assert resp.status_code == 200, resp.text
        assert (await _verify(owner, phone, resp.json()["dev_otp"])).status_code == 200

    # The hour passes: new devices can be sent codes again
    await _travel(phone, 3601)
    async with _new_client() as newcomer:
        assert (await _request(newcomer, phone)).status_code == 200


@pytest.mark.asyncio
async def test_parallel_requests_cannot_pass_the_throttles(otp_settings):
    """Regression: the throttles were read before the new code was written,
    with nothing in between, so parallel requests all passed: 8 at once sent
    8 SMS inside one resend window."""
    # Fresh browsers: exactly the per-phone cap gets through
    phone = "+919200000012"

    async def from_new_browser() -> int:
        async with _new_client() as c:
            return (await _request(c, phone)).status_code

    statuses = await asyncio.gather(*(from_new_browser() for _ in range(8)))
    cap = settings.OTP_MAX_SENDS_PER_HOUR
    assert sorted(statuses) == [200] * cap + [429] * (8 - cap)
    assert await _codes_sent(phone) == cap

    # One browser (several tabs): exactly one code per resend window
    phone = "+919200000013"
    async with _new_client() as first_tab:
        assert (await _request(first_tab, phone)).status_code == 200
        device_id = _device(first_tab)
    await _travel(phone, 61)

    async def from_tab() -> int:
        async with _new_client(device_id) as tab:
            return (await _request(tab, phone)).status_code

    statuses = await asyncio.gather(*(from_tab() for _ in range(6)))
    assert sorted(statuses) == [200] + [429] * 5
    assert await _codes_sent(phone) == 2


@pytest.mark.asyncio
async def test_typo_on_the_next_login_is_not_a_lockout(client, otp_settings):
    """Regression: wrong codes on an abandoned code used to count against the
    phone after a successful login, so one typo next time locked it."""
    phone = "+919200000007"
    first = (await _request(client, phone)).json()["dev_otp"]
    for _ in range(settings.OTP_MAX_ATTEMPTS - 1):
        assert (await _verify(client, phone, _wrong(first))).status_code == 401

    await _travel(phone, 61)
    second = (await _request(client, phone)).json()["dev_otp"]
    assert (await _verify(client, phone, second)).status_code == 200
    assert (await client.post("/api/auth/logout")).status_code == 200

    await _travel(phone, 120)
    resp = await _request(client, phone)
    assert resp.status_code == 200, resp.text
    third = resp.json()["dev_otp"]
    resp = await _verify(client, phone, _wrong(third))
    assert resp.status_code == 401, resp.text
    assert (await _verify(client, phone, third)).status_code == 200


async def _verify_in_parallel(phone: str, device_id: str, codes: list[str]) -> list[int]:
    """Each guess from its own tab of the requesting browser, all in flight at once."""
    async def one(code: str) -> int:
        async with _new_client(device_id) as c:
            return (await _verify(c, phone, code)).status_code
    return list(await asyncio.gather(*(one(code) for code in codes)))


@pytest.mark.asyncio
async def test_parallel_wrong_guesses_get_only_max_attempts_checks(otp_settings):
    """Regression: the attempt count was read, incremented in Python and
    written back, so 20 parallel guesses were all checked and the count
    ended at 1-2 (lost updates) with the code still usable."""
    phone = "+919200000008"
    async with _new_client() as c:
        otp = (await _request(c, phone)).json()["dev_otp"]
        device_id = _device(c)
    wrong = [_wrong(otp, n) for n in range(20)]

    statuses = await _verify_in_parallel(phone, device_id, wrong)

    # Exactly OTP_MAX_ATTEMPTS guesses were checked: max-1 plain misses, then
    # the one that used the code up (429); every other guess was refused unchecked
    assert statuses.count(401) == settings.OTP_MAX_ATTEMPTS - 1
    assert statuses.count(429) == len(wrong) - (settings.OTP_MAX_ATTEMPTS - 1)
    assert await _attempts(phone) == [settings.OTP_MAX_ATTEMPTS]
    async with _new_client(device_id) as c:
        assert (await _verify(c, phone, otp)).status_code == 429


@pytest.mark.asyncio
async def test_a_code_logs_in_only_once_under_parallel_use(otp_settings):
    phone = "+919200000009"
    async with _new_client() as c:
        otp = (await _request(c, phone)).json()["dev_otp"]
        device_id = _device(c)

    statuses = await _verify_in_parallel(phone, device_id, [otp] * 5)
    assert sorted(statuses) == [200, 401, 401, 401, 401]
