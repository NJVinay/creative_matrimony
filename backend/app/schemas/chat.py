from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.profile import ProfilePublicOut

class InterestOut(BaseModel):
    id: int
    sender: ProfilePublicOut
    receiver: ProfilePublicOut
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ChatMessageOut(BaseModel):
    id: int
    sender_id: int
    content: str
    created_at: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)

class ChatParticipantUserOut(BaseModel):
    id: int
    profile: ProfilePublicOut | None

    model_config = ConfigDict(from_attributes=True)

class ChatParticipantOut(BaseModel):
    user_id: int
    user: ChatParticipantUserOut | None
    
    model_config = ConfigDict(from_attributes=True)

class ChatRoomOut(BaseModel):
    id: int
    is_active: bool
    participants: List[ChatParticipantOut]
    latest_message: Optional[ChatMessageOut] = None  # inbox list preview

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str
