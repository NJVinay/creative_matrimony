"""
Test fixtures — file-based SQLite test DB, cookie-authenticated clients.
Environment is configured BEFORE app modules import settings.
"""

import os
import asyncio
import pathlib

# ── Must run before any `app.*` import ─────────────────────
TEST_DB_PATH = pathlib.Path(__file__).parent / "test.db"
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["DEBUG"] = "false"
os.environ["RESEND_API_KEY"] = ""  # emails are no-ops in tests
# Generous limits so the suite never trips throttles
os.environ["OTP_RATE_LIMIT_PER_IP"] = "1000/hour"
os.environ["GLOBAL_RATE_LIMIT"] = "10000/minute"
os.environ["OTP_COOLDOWN_SECONDS"] = "1"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.models  # noqa: F401 — register all tables on Base.metadata
from app.database import engine, async_session, Base
from app.main import application


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database():
    """Fresh schema for the whole test session."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="https://testserver") as c:
        yield c


@pytest_asyncio.fixture
async def db():
    async with async_session() as session:
        yield session
        await session.commit()


async def login(client: AsyncClient, phone: str) -> dict:
    """Register/login a user through the real OTP flow.
    The raw OTP comes from calling the service directly (mock provider)."""
    from app.services.otp_service import create_otp

    async with async_session() as session:
        otp = await create_otp(session, phone)
        await session.commit()

    resp = await client.post("/api/auth/otp/verify", json={"phone": phone, "otp": otp})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def make_client(phone: str) -> AsyncClient:
    """Standalone authenticated client (own cookie jar)."""
    transport = ASGITransport(app=application)
    c = AsyncClient(transport=transport, base_url="https://testserver")
    await login(c, phone)
    return c


async def create_profile(client: AsyncClient, *, display_name: str, gender: str,
                         verified_only_opt_in: bool = False, **extra) -> dict:
    payload = {
        "profile_mode": "self",
        "display_name": display_name,
        "gender": gender,
        "date_of_birth": "1995-05-10",
        "city_village": "Hyderabad",
        "state": "Telangana",
        "verified_only_opt_in": verified_only_opt_in,
        **extra,
    }
    resp = await client.post("/api/profiles", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()
