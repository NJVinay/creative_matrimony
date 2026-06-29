"""
Expert API endpoints.
Trace: @context_documents/MVP_BACKLOG.md Epic I
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.models.expert import ExpertInquiry
from app.schemas.expert import ExpertInquiryCreate, ExpertInquiryOut
from app.middleware.auth import get_current_user, require_roles

router = APIRouter(prefix="/expert", tags=["Expert Services"])

@router.post("/inquiry", response_model=ExpertInquiryOut)
async def create_inquiry(
    data: ExpertInquiryCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Submit an inquiry for expert services."""
    inquiry = ExpertInquiry(
        user_id=user.id,
        **data.model_dump()
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return inquiry

@router.get("/inquiries", response_model=list[ExpertInquiryOut])
async def list_my_inquiries(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """List my past inquiries."""
    result = await db.execute(select(ExpertInquiry).where(ExpertInquiry.user_id == user.id).order_by(ExpertInquiry.created_at.desc()))
    return result.scalars().all()
    
# Admin Endpoint for Listing
@router.get("/admin/all", response_model=list[ExpertInquiryOut])
async def list_all_inquiries(
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Admin: List all inquiries."""
    result = await db.execute(select(ExpertInquiry).order_by(ExpertInquiry.created_at.desc()))
    return result.scalars().all()

@router.patch("/admin/{inquiry_id}/resolve")
async def resolve_inquiry(
    inquiry_id: int,
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Admin: Mark an inquiry as resolved."""
    inquiry = await db.get(ExpertInquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
        
    inquiry.is_resolved = True
    await db.commit()
    return {"status": "resolved"}
