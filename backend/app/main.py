"""
FastAPI application factory.
Trace: @context_documents/TECH_STACK_PLANNER.md §1–§2, @context_documents/SECURITY_PLANNER.md §2
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.rate_limit import limiter

from app.config import settings
from app.database import init_db

# ── Rate limiter imported from app.rate_limit ─────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables (dev). Shutdown: cleanup."""
    # Import models so Base.metadata knows all tables
    import app.models  # noqa: F401
    await init_db()
    print(f"✅  {settings.APP_NAME} ready — database initialized")
    yield
    print("👋  Shutting down...")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Creative Matrimony MVP — Telugu-first matrimonial + horoscope platform API",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limiting ─────────────────────────────────────
    application.state.limiter = limiter
    application.add_middleware(SlowAPIMiddleware)
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Routers ───────────────────────────────────────────
    from app.api.auth import router as auth_router
    from app.api.profiles import router as profiles_router
    from app.api.taxonomy import router as taxonomy_router, admin_router as taxonomy_admin_router
    from app.api.search import router as search_router
    from app.api.payments import router as payments_router
    from app.api.admin import router as admin_router
    from app.api.notifications import router as notifications_router
    from app.api.matches import router as matches_router
    from app.api.chat import router as chat_router
    from app.api.horoscope import router as horoscope_router
    from app.api.expert import router as expert_router
    from app.api.photos import router as photos_router, admin_router as photos_admin_router
    from app.api.reports import router as reports_router, admin_router as reports_admin_router

    application.include_router(auth_router, prefix=settings.API_PREFIX)
    application.include_router(profiles_router, prefix=settings.API_PREFIX)
    application.include_router(taxonomy_router, prefix=settings.API_PREFIX)
    application.include_router(taxonomy_admin_router, prefix=settings.API_PREFIX)
    application.include_router(search_router, prefix=settings.API_PREFIX)
    application.include_router(matches_router, prefix=settings.API_PREFIX)
    application.include_router(chat_router, prefix=settings.API_PREFIX)
    application.include_router(horoscope_router, prefix=settings.API_PREFIX)
    application.include_router(expert_router, prefix=settings.API_PREFIX)
    application.include_router(payments_router, prefix=settings.API_PREFIX)
    application.include_router(admin_router, prefix=settings.API_PREFIX)
    application.include_router(notifications_router, prefix=settings.API_PREFIX)
    application.include_router(photos_router, prefix=settings.API_PREFIX)
    application.include_router(photos_admin_router, prefix=settings.API_PREFIX)
    application.include_router(reports_router, prefix=settings.API_PREFIX)
    application.include_router(reports_admin_router, prefix=settings.API_PREFIX)

    # ── Static file serving for uploads ─────────────────
    import os
    os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    application.mount("/uploads", StaticFiles(directory=settings.LOCAL_STORAGE_DIR), name="uploads")

    # ── Health check ──────────────────────────────────────
    @application.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}

    return application


application = create_app()
