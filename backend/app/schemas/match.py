from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict
from app.schemas.profile import ProfilePublicOut

class PreferenceBase(BaseModel):
    min_age: Optional[int] = 18
    max_age: Optional[int] = 35
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    country: Optional[str] = "India"
    state: Optional[str] = None
    
    # JSON fields
    marital_status: Optional[List[str]] = None
    religion_id: Optional[List[int]] = None
    community_id: Optional[List[int]] = None
    education_level: Optional[List[str]] = None
    occupation_category: Optional[List[str]] = None

class PreferenceUpdate(PreferenceBase):
    pass

class PreferenceOut(PreferenceBase):
    id: int
    profile_id: int
    updated_at: Any
    
    model_config = ConfigDict(from_attributes=True)

class MatchRecommendation(BaseModel):
    profile: ProfilePublicOut
    score: int
    reasons: List[str]
    confidence: int = 100  # share of criteria evaluated (rises when horoscope data exists)
