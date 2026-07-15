"""Pydantic schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr, Field


class OTPRequestIn(BaseModel):
    phone: str = Field(..., pattern=r"^\+?\d{10,15}$", description="Phone number with optional country code")
    device_fingerprint: str | None = Field(None, max_length=255)


class OTPRequestOut(BaseModel):
    message: str = "OTP sent successfully"
    expires_in_seconds: int = 300
    # Populated only when OTP_DEV_ECHO is enabled (dev/staging testing aid)
    dev_otp: str | None = None


class OTPVerifyIn(BaseModel):
    phone: str = Field(..., pattern=r"^\+?\d{10,15}$")
    otp: str = Field(..., min_length=6, max_length=6)


class OTPVerifyOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool


class TokenRefreshIn(BaseModel):
    refresh_token: str


class TokenRefreshOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ContactUpdateIn(BaseModel):
    email: EmailStr | None = None
    email_digest_opt_in: bool | None = None


class UserOut(BaseModel):
    id: int
    phone: str
    email: str | None = None
    role: str
    is_verified: bool
    is_banned: bool
    email_digest_opt_in: bool = False

    model_config = {"from_attributes": True}
