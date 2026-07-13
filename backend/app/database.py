"""
Async SQLAlchemy engine + session factory.
aiosqlite for local dev; asyncpg for production PostgreSQL (e.g. Neon).
"""

import re

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Accept the URL formats hosting providers hand out.
    Neon/Heroku style `postgres://` or `postgresql://` becomes the asyncpg
    dialect, and `sslmode=require` (libpq syntax) becomes asyncpg's `ssl=require`.
    """
    url = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", url)
    url = url.replace("sslmode=", "ssl=")
    # asyncpg does not understand channel_binding (Neon adds it)
    url = re.sub(r"[&?]channel_binding=[^&]*", "", url)
    return url


DATABASE_URL = _normalize_db_url(settings.DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    # SQLite needs this for async
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables (dev convenience — use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
