"""
Application settings — loaded from environment / .env file.
All external service configs are mock-ready for local development.
"""

import json

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "Creative Matrimony API"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # ── Database (SQLite for local dev) ──────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"

    # ── Auth / JWT ───────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OTP ──────────────────────────────────────────────
    OTP_LENGTH: int = 6
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    OTP_MAX_ATTEMPTS: int = 3
    OTP_COOLDOWN_SECONDS: int = 600  # 10 minutes after max attempts
    OTP_PROVIDER: str = "mock"  # "mock" | "fast2sms" | "whatsapp"
    # Testing aid: when true, the OTP is returned in the API response
    # (the frontend shows it in a toast). ONLY for dev/staging — turn OFF
    # before real users; anyone could log in as any phone number.
    OTP_DEV_ECHO: bool = False

    # ── OTP delivery: Fast2SMS (India-only SMS, shared DLT route) ──
    FAST2SMS_API_KEY: str = ""

    # ── OTP delivery: WhatsApp Cloud API (Meta) ─────────────────────
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_TEMPLATE_NAME: str = "otp_verification"
    WHATSAPP_TEMPLATE_LANGUAGE: str = "en"

    # ── Rate Limiting ────────────────────────────────────
    OTP_RATE_LIMIT_PER_PHONE: str = "5/minute"
    OTP_RATE_LIMIT_PER_IP: str = "20/hour"
    GLOBAL_RATE_LIMIT: str = "100/minute"

    # ── CORS ─────────────────────────────────────────────
    # Accepts a bare URL, a comma-separated list, or (for backward
    # compatibility) a JSON array. Kept as `str` rather than `List[str]`
    # because pydantic-settings JSON-decodes list-typed env vars *before*
    # any validator runs, which would reject a plain URL outright.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # ── Auth cookies ─────────────────────────────────────
    # Set COOKIE_SAMESITE="none" when the frontend runs on a different
    # domain than the API (e.g. Vercel frontend + Render backend).
    COOKIE_SAMESITE: str = "lax"  # "lax" | "none" | "strict"
    COOKIE_SECURE: bool = True

    # ── Content moderation ───────────────────────────────
    # Extra blocked words/phrases for chat (comma-separated), added to the
    # built-in list in app/services/moderation.py. Whole-word matching;
    # a trailing "*" also matches longer forms (e.g. "idiot*").
    MODERATION_BLOCKED_TERMS: str = ""

    # ── File Storage (local for dev) ─────────────────────
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    LOCAL_STORAGE_DIR: str = "./uploads"

    # ── Payment Provider ─────────────────────────────────
    PAYMENT_PROVIDER: str = "mock"  # "mock" | "razorpay" (when implemented)
    PAYMENT_PROVIDER_SECRET: str = "MOCK_RAZORPAY_SECRET_DO_NOT_USE_IN_PROD"

    # ── Email (Resend) ───────────────────────────────────
    # Empty key disables outbound email (calls become no-ops that log).
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Creative Matrimony <onboarding@resend.dev>"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
