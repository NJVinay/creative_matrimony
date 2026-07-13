"""Pydantic schemas for auth endpoints."""

from pydantic import BaseModel, Field


class OTPRequestIn(BaseModel):
    phone: str = Field(..., pattern=r"^\+?\d{10,15}$", description="Phone number with optional country code")
    device_fingerprint: str | None = Field(None, max_length=255)


class OTPRequestOut(BaseModel):
    message: str = "OTP sent successfully"
    expires_in_seconds: int = 300


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


class UserOut(BaseModel):
    id: int
    phone: str
    role: str
    is_verified: bool
    is_banned: bool

    model_config = {"from_attributes": True}
