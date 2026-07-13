"""
Application settings — loaded from environment / .env file.
All external service configs are mock-ready for local development.
"""

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
    OTP_PROVIDER: str = "mock"  # "mock" | "twilio" | "msg91"

    # ── Rate Limiting ────────────────────────────────────
    OTP_RATE_LIMIT_PER_PHONE: str = "5/minute"
    OTP_RATE_LIMIT_PER_IP: str = "20/hour"
    GLOBAL_RATE_LIMIT: str = "100/minute"

    # ── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ── File Storage (local for dev) ─────────────────────
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    LOCAL_STORAGE_DIR: str = "./uploads"

    # ── Payment Provider ─────────────────────────────────
    PAYMENT_PROVIDER: str = "mock"  # "mock" | "razorpay" (when implemented)
    PAYMENT_PROVIDER_SECRET: str = "MOCK_RAZORPAY_SECRET_DO_NOT_USE_IN_PROD"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
