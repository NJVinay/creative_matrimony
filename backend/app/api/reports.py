"""
Reports API — user-facing submit + admin queue.
Trace: @context_documents/MVP_BACKLOG.md Epic J
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models.report import Report, ReportReason, ReportStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportCreateIn(BaseModel):
    target_user_id: int
    reason: ReportReason
    evidence_text: str | None = Field(None, max_length=2000)


class ReportOut(BaseModel):
    id: int
    reporter_id: int
    target_user_id: int
    reason: str
    evidence_text: str | None
    status: str
    reviewed_by: int | None
    reviewed_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def submit_report(
    body: ReportCreateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Submit a report against another user."""
    if body.target_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot report yourself.")

    # Verify target exists
    target = await db.get(User, body.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found.")

    report = Report(
        reporter_id=user.id,
        target_user_id=body.target_user_id,
        reason=body.reason,
        evidence_text=body.evidence_text,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


# ── Admin moderation ──────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin – Reports"],
    dependencies=[Depends(require_roles(UserRole.admin, UserRole.moderator))],
)


@admin_router.get("", response_model=list[ReportOut])
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: ReportStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List reports, optionally filtered by status."""
    stmt = select(Report).order_by(Report.created_at.desc()).offset(offset).limit(limit)
    if status_filter is not None:
        stmt = stmt.where(Report.status == status_filter)
    result = await db.execute(stmt)
    return result.scalars().all()


@admin_router.patch("/{report_id}/resolve", response_model=ReportOut)
async def resolve_report(
    report_id: int,
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.moderator))],
    db: Annotated[AsyncSession, Depends(get_db)],
    new_status: ReportStatus = ReportStatus.resolved,
):
    """Mark a report as resolved, investigating, or dismissed."""
    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    report.status = new_status
    report.reviewed_by = user.id
    report.reviewed_at = datetime.utcnow()
    await db.flush()
    await db.refresh(report)
    return report
