"""Pydantic schemas for profile endpoints."""

from datetime import date, datetime
import re
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from app.services.moderation import contains_contact_info
from app.services.profile_service import meets_minimum_age, minimum_age_for

# Free-text fields shown to other members: no contact details allowed.
_PUBLIC_TEXT_FIELDS = ("display_name", "bio", "family_details", "partner_preferences")


def _strip_html(v):
    if isinstance(v, str):
        return re.sub(r'<[^>]*>', '', v)
    return v


def _reject_contact_info(v):
    if isinstance(v, str) and contains_contact_info(v):
        raise PydanticCustomError(
            "contact_info",
            "Please remove phone numbers, email addresses and social media handles. "
            "Members connect through interests and chat on the platform.",
        )
    return v


class ProfileCreateIn(BaseModel):
    profile_mode: str = Field(..., pattern=r"^(self|parent)$")
    guardian_relationship: str | None = Field(None, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    gender: str = Field(..., pattern=r"^(male|female|other)$")
    date_of_birth: date
    height_cm: int | None = Field(None, ge=100, le=250)
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
    # Women-first safety opt-in: verified-only visibility from day one.
    # Photo blur defaults ON for female profiles regardless (reversible in settings).
    verified_only_opt_in: bool = False

    @field_validator(*_PUBLIC_TEXT_FIELDS, mode="before")
    @classmethod
    def sanitize_html(cls, v):
        return _strip_html(v)

    @field_validator(*_PUBLIC_TEXT_FIELDS)
    @classmethod
    def no_contact_info(cls, v):
        return _reject_contact_info(v)

    @field_validator("date_of_birth")
    @classmethod
    def legal_marriage_age(cls, v: date, info: ValidationInfo) -> date:
        """Indian legal marriage age: 18 for women, 21 for men (and others)."""
        gender = info.data.get("gender")
        if gender is None:  # gender failed its own validation; that error is reported
            return v
        if v > date.today():
            raise PydanticCustomError("dob_future", "Date of birth cannot be in the future.")
        if not meets_minimum_age(v, gender):
            who = {"female": " for women", "male": " for men"}.get(gender, "")
            raise PydanticCustomError(
                "under_age",
                f"Must be at least {minimum_age_for(gender)} years old to register "
                f"(the legal minimum marriage age{who} in India).",
            )
        return v


class ProfileUpdateIn(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=100)
    height_cm: int | None = Field(None, ge=100, le=250)
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

    @field_validator(*_PUBLIC_TEXT_FIELDS, mode="before")
    @classmethod
    def sanitize_html(cls, v):
        return _strip_html(v)

    @field_validator(*_PUBLIC_TEXT_FIELDS)
    @classmethod
    def no_contact_info(cls, v):
        return _reject_contact_info(v)


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
    height_cm: int | None
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
    created_at: datetime

    model_config = {"from_attributes": True}


class PhotoRefOut(BaseModel):
    url: str  # path on the API origin, e.g. /uploads/profiles/...


class ProfilePublicOut(BaseModel):
    """Public view — enforces location privacy (city+state only), no phone/email."""
    id: int
    display_name: str
    gender: str
    age: int  # calculated, not raw DOB
    height_cm: int | None = None
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
    # Filled only by list endpoints that resolve photo access for the viewer
    # (match recommendations, search): the display photo when the viewer may
    # see it, else None. A missing photo alone never means "locked" — clients
    # read photo_locked, which only those endpoints set (approved photos exist,
    # blurred until mutual interest, not yet unlocked for this viewer).
    profile_photo: PhotoRefOut | None = None
    photo_locked: bool = False


class ProfilePhotoOut(BaseModel):
    id: int
    profile_id: int
    # None (with locked=True) when the owner blurs photos until mutual interest
    # and the viewer has not unlocked them: the file URL is never handed out.
    storage_key: str | None
    locked: bool = False
    is_primary: bool
    is_approved: bool | None
    rejection_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
