"""Pydantic schemas for profile endpoints."""

from datetime import date
import re
from pydantic import BaseModel, Field, field_validator


class ProfileCreateIn(BaseModel):
    profile_mode: str = Field(..., pattern=r"^(self|parent)$")
    guardian_relationship: str | None = Field(None, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    gender: str = Field(..., pattern=r"^(male|female|other)$")
    date_of_birth: date
    bio: str | None = Field(None, max_length=2000)
    city_village: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    country: str = "India"
    religion_id: int | None = None
    community_id: int | None = None
    subcaste_id: int | None = None
    education_level: str | None = None
    occupation_category: str | None = None
    marital_status: str | None = None
    identity_language_group: str = "Telugu"
    family_details: str | None = None
    partner_preferences: str | None = None

    @field_validator("bio", "display_name", "family_details", "partner_preferences", mode="before")
    @classmethod
    def sanitize_html(cls, v):
        if isinstance(v, str):
            return re.sub(r'<[^>]*>', '', v)
        return v


class ProfileUpdateIn(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=100)
    bio: str | None = Field(None, max_length=2000)
    city_village: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    religion_id: int | None = None
    community_id: int | None = None
    subcaste_id: int | None = None
    education_level: str | None = None
    occupation_category: str | None = None
    marital_status: str | None = None
    family_details: str | None = None
    partner_preferences: str | None = None

    @field_validator("bio", "display_name", "family_details", "partner_preferences", mode="before")
    @classmethod
    def sanitize_html(cls, v):
        if isinstance(v, str):
            return re.sub(r'<[^>]*>', '', v)
        return v


class PrivacyUpdateIn(BaseModel):
    visibility: str | None = Field(None, pattern=r"^(public|verified_only|hidden)$")
    photo_blur_until_mutual: bool | None = None
    hide_from_search: bool | None = None


class ProfileOut(BaseModel):
    id: int
    user_id: int
    profile_mode: str
    guardian_relationship: str | None
    display_name: str
    gender: str
    date_of_birth: date
    bio: str | None
    city_village: str | None
    state: str | None
    country: str
    religion_id: int | None
    community_id: int | None
    subcaste_id: int | None
    education_level: str | None
    occupation_category: str | None
    marital_status: str | None
    completion_pct: float
    is_active: bool
    visibility: str
    photo_blur_until_mutual: bool
    created_at: str

    model_config = {"from_attributes": True}


class ProfilePublicOut(BaseModel):
    """Public view — enforces location privacy (city+state only), no phone/email."""
    id: int
    display_name: str
    gender: str
    age: int  # calculated, not raw DOB
    bio: str | None
    city_village: str | None
    state: str | None
    religion_id: int | None
    community_id: int | None
    education_level: str | None
    occupation_category: str | None
    marital_status: str | None
    is_verified: bool
    completion_pct: float
    photo_blur_until_mutual: bool = False


class ProfilePhotoOut(BaseModel):
    id: int
    profile_id: int
    storage_key: str
    is_primary: bool
    is_approved: bool | None
    rejection_reason: str | None
    created_at: str

    model_config = {"from_attributes": True}
