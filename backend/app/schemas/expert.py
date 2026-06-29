from typing import Optional
from pydantic import BaseModel
from app.models.expert import ExpertCategory

class ExpertInquiryCreate(BaseModel):
    category: ExpertCategory
    message: str
    preferred_contact_time: Optional[str] = None

class ExpertInquiryOut(BaseModel):
    id: int
    user_id: int
    category: ExpertCategory
    message: str
    created_at: str
    is_resolved: bool

    class Config:
        from_attributes = True
