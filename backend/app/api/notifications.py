"""
Notification API.
Trace: @context_documents/MVP_BACKLOG.md Epic K
"""

from typing import Annotated, List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: Any # datetime

@router.get("", response_model=List[NotificationOut])
async def list_notifications(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0
):
    """Get my notifications."""
    return await NotificationService.get_user_notifications(db, user.id, limit, offset)

@router.patch("/{id}/read")
async def mark_read(
    id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Mark notification as read."""
    await NotificationService.mark_as_read(db, id, user.id)
    return {"status": "marked_read"}

@router.patch("/read-all")
async def mark_all_read(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Mark all notifications as read."""
    await NotificationService.mark_all_read(db, user.id)
    return {"status": "all_marked_read"}
