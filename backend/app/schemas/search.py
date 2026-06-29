"""Pydantic schemas for search endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional

from app.schemas.profile import ProfilePublicOut


class SearchRequest(BaseModel):
    min_age: int = Field(18, ge=18, le=99)
    max_age: int = Field(40, ge=18, le=99)
    gender: Optional[str] = Field(None, pattern=r"^(male|female|other)$")
    marital_status: Optional[List[str]] = None
    religion_id: Optional[int] = None
    community_id: Optional[List[int]] = None
    city_village: Optional[str] = None
    state: Optional[str] = None
    education_level: Optional[str] = None
    occupation_category: Optional[str] = None
    
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=50)


class SearchResponse(BaseModel):
    results: List[ProfilePublicOut]
    page: int
    limit: int
    total: int = 0
