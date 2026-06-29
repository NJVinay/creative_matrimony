"""Pydantic schemas for taxonomy endpoints."""

from pydantic import BaseModel, Field


class TaxonomyItemOut(BaseModel):
    id: int
    canonical_id: str
    name_en: str
    name_te: str | None

    model_config = {"from_attributes": True}


class RegionGroupOut(TaxonomyItemOut):
    is_enabled: bool
    sort_order: int


class LanguageGroupOut(TaxonomyItemOut):
    is_enabled: bool


class CommunityOut(TaxonomyItemOut):
    religion_id: int
    language_group_id: int


class SubCasteOut(TaxonomyItemOut):
    community_id: int


class TaxonomyCreateIn(BaseModel):
    canonical_id: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9_]+$")
    name_en: str = Field(..., min_length=1, max_length=200)
    name_te: str | None = Field(None, max_length=200)


class CommunityCreateIn(TaxonomyCreateIn):
    religion_id: int
    language_group_id: int


class SubCasteCreateIn(TaxonomyCreateIn):
    community_id: int


class TaxonomySuggestIn(BaseModel):
    """User submits an unknown taxonomy value for moderation."""
    value: str = Field(..., min_length=1, max_length=200)
    field_name: str = Field(..., pattern=r"^(religion|community|subcaste)$")


class TaxonomySuggestOut(BaseModel):
    id: int
    message: str = "Your suggestion has been submitted for review."

class TaxonomySuggestionOut(BaseModel):
    id: int
    user_id: int
    user_submitted_value: str
    field_name: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}

class TaxonomyResolveIn(BaseModel):
    action: str = Field(..., pattern=r"^(approve|reject)$")
    target_id: int | None = None # Required if action is approve

