"""
Weekly digest — top match recommendations by email, consent-gated.
Only users who set an email AND opted in (email_digest_opt_in) receive it.
Triggered by POST /api/admin/digest/send (point a weekly cron at it —
e.g. GitHub Actions, Render Cron, or an uptime pinger).
Trace: @context_documents/MVP_BACKLOG.md Epic G2
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.profile import Profile
from app.services.matching_service import MatchingService
from app.services.email_service import send_email

DIGEST_MATCH_COUNT = 5


def _render_digest_html(display_name: str, matches: list) -> str:
    rows = []
    for profile, score, reasons, _confidence in matches:
        reason_text = " · ".join(reasons[:3])
        rows.append(
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee'>"
            f"<strong>{profile.display_name}</strong>, {profile.age}"
            f"<br><span style='color:#666;font-size:13px'>{profile.city_village or ''}"
            f"{', ' + profile.state if profile.state else ''}</span>"
            f"<br><span style='color:#888;font-size:12px'>{reason_text}</span></td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right'>"
            f"<strong>{score}%</strong></td>"
            f"</tr>"
        )
    return (
        f"<div style='font-family:sans-serif;max-width:520px;margin:auto'>"
        f"<h2 style='color:#b91c1c'>Your weekly matches</h2>"
        f"<p>Namaste {display_name}, here are this week's top matches for you:</p>"
        f"<table style='width:100%;border-collapse:collapse'>{''.join(rows)}</table>"
        f"<p style='color:#888;font-size:12px;margin-top:16px'>"
        f"You receive this because you opted in to the weekly digest. "
        f"Turn it off anytime in Settings.</p>"
        f"</div>"
    )


async def send_weekly_digest(db: AsyncSession) -> dict:
    """Send the digest to every consented user. Returns a summary."""
    result = await db.execute(
        select(User).where(
            User.email.isnot(None),
            User.email_digest_opt_in.is_(True),
            User.is_banned.is_(False),
        )
    )
    users = result.scalars().all()

    sent, skipped = 0, 0
    for user in users:
        profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
        if not profile:
            skipped += 1
            continue

        matches = await MatchingService.get_recommendations(db, profile.id, DIGEST_MATCH_COUNT)
        if not matches:
            skipped += 1
            continue

        ok = await send_email(
            to=user.email,
            subject="Your weekly matches — Creative Matrimony",
            html=_render_digest_html(profile.display_name, matches),
        )
        sent += 1 if ok else 0
        skipped += 0 if ok else 1

    return {"eligible_users": len(users), "sent": sent, "skipped": skipped}
