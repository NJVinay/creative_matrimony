"""
Expert API endpoints — inquiries, consultation sessions, Personal Care mode.
Trace: @context_documents/MVP_BACKLOG.md Epic I
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.expert import (
    ExpertInquiry, ExpertSession, SessionStatus,
    CareAssignment, CareTask, CareCallLog, CareStatus,
)
from app.models.payment import UserSubscription
from app.models.notification import NotificationType
from app.schemas.expert import (
    ExpertInquiryCreate, ExpertInquiryOut, ExpertInquiryAdminOut,
    SessionCreate, SessionOut,
    CareAssignmentCreate, CareAssignmentOut,
    CareTaskCreate, CareTaskOut,
    CareCallLogCreate, CareCallLogOut,
)
from app.middleware.auth import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.services.email_service import send_email
from app.services.profile_service import get_profiles_by_user_ids

router = APIRouter(prefix="/expert", tags=["Expert Services"])

# Tier-gated session quotas per calendar month (Epic I1).
# Paid/trial subscribers get more and longer sessions.
FREE_SESSIONS_PER_MONTH = 1
PAID_SESSIONS_PER_MONTH = 4
FREE_MAX_DURATION = 30
PAID_MAX_DURATION = 60

EXPERT_ROLES = (
    UserRole.admin, UserRole.expert,
    UserRole.horoscope_expert, UserRole.personal_care_expert,
)


async def _has_active_subscription(db: AsyncSession, user_id: int) -> bool:
    sub = await db.scalar(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        ).limit(1)
    )
    return sub is not None


# ── Inquiries (existing) ────────────────────────────────────

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


# ── Epic I1: consultation session booking ───────────────────

@router.post("/sessions", response_model=SessionOut, status_code=201)
async def book_session(
    data: SessionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Book an expert consultation. Quota and duration are tier-gated."""
    scheduled = data.scheduled_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    if scheduled <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Session must be scheduled in the future.")

    is_paid = await _has_active_subscription(db, user.id)
    max_duration = PAID_MAX_DURATION if is_paid else FREE_MAX_DURATION
    quota = PAID_SESSIONS_PER_MONTH if is_paid else FREE_SESSIONS_PER_MONTH

    if data.duration_minutes > max_duration:
        raise HTTPException(
            status_code=400,
            detail=f"Your plan allows sessions up to {max_duration} minutes.",
        )

    # Count non-cancelled sessions booked this calendar month
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = await db.scalar(
        select(func.count(ExpertSession.id)).where(
            ExpertSession.user_id == user.id,
            ExpertSession.status != SessionStatus.cancelled,
            ExpertSession.created_at >= month_start.replace(tzinfo=None),
        )
    )
    if (used or 0) >= quota:
        raise HTTPException(
            status_code=400,
            detail=f"Monthly session limit reached ({quota}). Upgrade your plan for more sessions.",
        )

    session = ExpertSession(
        user_id=user.id,
        category=data.category,
        scheduled_at=scheduled.replace(tzinfo=None),  # stored naive-UTC like other timestamps
        duration_minutes=data.duration_minutes,
        notes=data.notes,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    await NotificationService.create_notification(
        db=db,
        user_id=user.id,
        type=NotificationType.system,
        title="Consultation requested",
        body=f"Your expert session request for {scheduled.strftime('%d %b %Y, %H:%M')} UTC was received.",
        data={"session_id": session.id},
    )
    return session


@router.get("/sessions", response_model=list[SessionOut])
async def list_my_sessions(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List my consultation sessions."""
    result = await db.execute(
        select(ExpertSession)
        .where(ExpertSession.user_id == user.id)
        .order_by(ExpertSession.scheduled_at.desc())
    )
    return result.scalars().all()


@router.patch("/sessions/{session_id}/cancel", response_model=SessionOut)
async def cancel_my_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Cancel one of my sessions."""
    session = await db.get(ExpertSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status in (SessionStatus.completed, SessionStatus.cancelled):
        raise HTTPException(status_code=400, detail="Session can no longer be cancelled.")
    session.status = SessionStatus.cancelled
    await db.commit()
    await db.refresh(session)
    return session


# ── Admin/expert: session management + reminders ────────────

@router.get("/admin/sessions", response_model=list[SessionOut])
async def list_all_sessions(
    user: Annotated[User, Depends(require_roles(*EXPERT_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin/expert: list all sessions."""
    result = await db.execute(select(ExpertSession).order_by(ExpertSession.scheduled_at.desc()))
    return result.scalars().all()


@router.patch("/admin/sessions/{session_id}/confirm", response_model=SessionOut)
async def confirm_session(
    session_id: int,
    user: Annotated[User, Depends(require_roles(*EXPERT_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin/expert: confirm a requested session and take assignment."""
    session = await db.get(ExpertSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.confirmed
    session.expert_user_id = user.id

    await NotificationService.create_notification(
        db=db,
        user_id=session.user_id,
        type=NotificationType.system,
        title="Consultation confirmed",
        body=f"Your expert session on {session.scheduled_at.strftime('%d %b %Y, %H:%M')} UTC is confirmed.",
        data={"session_id": session.id},
    )
    member = await db.get(User, session.user_id)
    if member and member.email:
        await send_email(
            to=member.email,
            subject="Your expert consultation is confirmed — Creative Matrimony",
            html=(
                f"<p>Namaste,</p><p>Your expert consultation is confirmed for "
                f"<strong>{session.scheduled_at.strftime('%d %b %Y, %H:%M')} UTC</strong> "
                f"({session.duration_minutes} minutes).</p>"
            ),
        )
    await db.commit()
    await db.refresh(session)
    return session


@router.patch("/admin/sessions/{session_id}/complete", response_model=SessionOut)
async def complete_session(
    session_id: int,
    user: Annotated[User, Depends(require_roles(*EXPERT_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin/expert: mark a session completed."""
    session = await db.get(ExpertSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.completed
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/admin/sessions/send-reminders")
async def send_session_reminders(
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send reminders (in-app + email) for confirmed sessions in the next 24h.
    Point a daily cron at this endpoint."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_end = now + timedelta(hours=24)
    result = await db.execute(
        select(ExpertSession).where(
            ExpertSession.status == SessionStatus.confirmed,
            ExpertSession.reminder_sent.is_(False),
            ExpertSession.scheduled_at >= now,
            ExpertSession.scheduled_at <= window_end,
        )
    )
    sessions = result.scalars().all()
    sent = 0
    for session in sessions:
        await NotificationService.create_notification(
            db=db,
            user_id=session.user_id,
            type=NotificationType.system,
            title="Consultation reminder",
            body=f"Reminder: your expert session is at {session.scheduled_at.strftime('%d %b %Y, %H:%M')} UTC.",
            data={"session_id": session.id},
        )
        member = await db.get(User, session.user_id)
        if member and member.email:
            await send_email(
                to=member.email,
                subject="Reminder: expert consultation tomorrow — Creative Matrimony",
                html=(
                    f"<p>Reminder: your expert consultation is scheduled for "
                    f"<strong>{session.scheduled_at.strftime('%d %b %Y, %H:%M')} UTC</strong>.</p>"
                ),
            )
        session.reminder_sent = True
        sent += 1
    await db.commit()
    return {"reminders_sent": sent}


# ── Epic I2: Personal Care mode ─────────────────────────────

def _assignment_out(assignment: CareAssignment, tasks, call_logs) -> CareAssignmentOut:
    return CareAssignmentOut(
        id=assignment.id,
        user_id=assignment.user_id,
        expert_user_id=assignment.expert_user_id,
        status=assignment.status,
        service_fee=assignment.service_fee,
        notes=assignment.notes,
        created_at=assignment.created_at,
        tasks=[CareTaskOut.model_validate(t) for t in tasks],
        call_logs=[CareCallLogOut.model_validate(c) for c in call_logs],
    )


async def _load_assignment_children(db: AsyncSession, assignment_id: int):
    tasks = (await db.execute(
        select(CareTask).where(CareTask.assignment_id == assignment_id).order_by(CareTask.created_at)
    )).scalars().all()
    calls = (await db.execute(
        select(CareCallLog).where(CareCallLog.assignment_id == assignment_id).order_by(CareCallLog.called_at.desc())
    )).scalars().all()
    return tasks, calls


@router.get("/care/me", response_model=CareAssignmentOut | None)
async def my_care_assignment(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """My active Personal Care engagement, with checklist and call history."""
    assignment = await db.scalar(
        select(CareAssignment).where(
            CareAssignment.user_id == user.id,
            CareAssignment.status != CareStatus.closed,
        ).order_by(CareAssignment.created_at.desc()).limit(1)
    )
    if not assignment:
        return None
    tasks, calls = await _load_assignment_children(db, assignment.id)
    return _assignment_out(assignment, tasks, calls)


@router.post("/admin/care", response_model=CareAssignmentOut, status_code=201)
async def create_care_assignment(
    data: CareAssignmentCreate,
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: assign a dedicated expert to a member (service fee recorded;
    collection happens via the payment provider once Razorpay is integrated)."""
    member = await db.get(User, data.user_id)
    expert = await db.get(User, data.expert_user_id)
    if not member or not expert:
        raise HTTPException(status_code=404, detail="Member or expert not found")
    if expert.role not in EXPERT_ROLES:
        raise HTTPException(status_code=400, detail="Assigned user is not an expert")

    assignment = CareAssignment(
        user_id=data.user_id,
        expert_user_id=data.expert_user_id,
        service_fee=data.service_fee,
        notes=data.notes,
    )
    db.add(assignment)
    await db.flush()

    await NotificationService.create_notification(
        db=db,
        user_id=data.user_id,
        type=NotificationType.system,
        title="Personal Care activated",
        body="A dedicated expert has been assigned to help with your search.",
        data={"assignment_id": assignment.id},
    )
    await db.commit()
    await db.refresh(assignment)
    return _assignment_out(assignment, [], [])


async def _get_assignment_for_expert(db: AsyncSession, assignment_id: int, actor: User) -> CareAssignment:
    assignment = await db.get(CareAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    # Admin can manage any engagement; an expert only their own
    if actor.role != UserRole.admin and assignment.expert_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    return assignment


@router.post("/admin/care/{assignment_id}/tasks", response_model=CareTaskOut, status_code=201)
async def add_care_task(
    assignment_id: int,
    data: CareTaskCreate,
    user: Annotated[User, Depends(require_roles(*EXPERT_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Expert/admin: add a checklist task to a care engagement."""
    assignment = await _get_assignment_for_expert(db, assignment_id, user)
    task = CareTask(assignment_id=assignment.id, title=data.title)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/admin/care/tasks/{task_id}/toggle", response_model=CareTaskOut)
async def toggle_care_task(
    task_id: int,
    user: Annotated[User, Depends(require_roles(*EXPERT_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Expert/admin: toggle a checklist task done/undone."""
    task = await db.get(CareTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _get_assignment_for_expert(db, task.assignment_id, user)
    task.is_done = not task.is_done
    task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None) if task.is_done else None
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/admin/care/{assignment_id}/calls", response_model=CareCallLogOut, status_code=201)
async def log_care_call(
    assignment_id: int,
    data: CareCallLogCreate,
    user: Annotated[User, Depends(require_roles(*EXPERT_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Expert/admin: log a call made within a care engagement."""
    assignment = await _get_assignment_for_expert(db, assignment_id, user)
    call = CareCallLog(
        assignment_id=assignment.id,
        duration_minutes=data.duration_minutes,
        summary=data.summary,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


@router.patch("/admin/care/{assignment_id}/close", response_model=CareAssignmentOut)
async def close_care_assignment(
    assignment_id: int,
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: close a care engagement."""
    assignment = await db.get(CareAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.status = CareStatus.closed
    await db.commit()
    tasks, calls = await _load_assignment_children(db, assignment.id)
    return _assignment_out(assignment, tasks, calls)


# ── Admin: inquiries (existing) ─────────────────────────────

@router.get("/admin/all", response_model=list[ExpertInquiryAdminOut])
async def list_all_inquiries(
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Admin: List all inquiries, with the member's profile id + name for linking
    (a user id is not a profile id, so /profile/{user_id} shows the wrong person)."""
    result = await db.execute(select(ExpertInquiry).order_by(ExpertInquiry.created_at.desc()))
    inquiries = result.scalars().all()
    profiles = await get_profiles_by_user_ids(db, (i.user_id for i in inquiries))
    out = []
    for inquiry in inquiries:
        profile = profiles.get(inquiry.user_id)
        out.append(ExpertInquiryAdminOut(
            **ExpertInquiryOut.model_validate(inquiry).model_dump(),
            profile_id=profile.id if profile else None,
            display_name=profile.display_name if profile else None,
        ))
    return out

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
