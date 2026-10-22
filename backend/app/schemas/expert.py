from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.expert import ExpertCategory, SessionStatus, CareStatus

class ExpertInquiryCreate(BaseModel):
    category: ExpertCategory
    message: str
    preferred_contact_time: Optional[str] = None

class ExpertInquiryOut(BaseModel):
    id: int
    user_id: int
    category: ExpertCategory
    message: str
    created_at: datetime
    is_resolved: bool

    class Config:
        from_attributes = True

class ExpertInquiryAdminOut(ExpertInquiryOut):
    """Admin queue row: the member's profile id (for /profile links) and name."""
    profile_id: Optional[int] = None
    display_name: Optional[str] = None


# ── Epic I1: consultation sessions ──────────────────────────

class SessionCreate(BaseModel):
    category: ExpertCategory = ExpertCategory.matchmaking
    scheduled_at: datetime
    duration_minutes: int = Field(30, ge=15, le=120)
    notes: Optional[str] = Field(None, max_length=2000)

class SessionOut(BaseModel):
    id: int
    user_id: int
    expert_user_id: Optional[int]
    category: ExpertCategory
    scheduled_at: datetime
    duration_minutes: int
    status: SessionStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Epic I2: Personal Care mode ─────────────────────────────

class CareAssignmentCreate(BaseModel):
    user_id: int
    expert_user_id: int
    service_fee: int = Field(0, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)

class CareTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)

class CareCallLogCreate(BaseModel):
    duration_minutes: Optional[int] = Field(None, ge=0, le=600)
    summary: Optional[str] = Field(None, max_length=2000)

class CareTaskOut(BaseModel):
    id: int
    title: str
    is_done: bool
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class CareCallLogOut(BaseModel):
    id: int
    called_at: datetime
    duration_minutes: Optional[int]
    summary: Optional[str]

    class Config:
        from_attributes = True

class CareAssignmentOut(BaseModel):
    id: int
    user_id: int
    expert_user_id: int
    status: CareStatus
    service_fee: int
    notes: Optional[str]
    created_at: datetime
    tasks: list[CareTaskOut] = []
    call_logs: list[CareCallLogOut] = []
