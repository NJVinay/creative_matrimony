"""
Email service — Resend HTTP API (https://resend.com).
No SDK dependency; uses httpx which is already a project requirement.
Disabled (no-op with a console log) when RESEND_API_KEY is empty, so local
dev and tests never make network calls.
Trace: @context_documents/MVP_BACKLOG.md Epic G2, Epic I1
"""

import httpx

from app.config import settings

RESEND_ENDPOINT = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email. Returns True when accepted by Resend.

    Failures are logged and swallowed — email is a side-channel and must
    never break the calling request.
    """
    if not settings.RESEND_API_KEY:
        print(f"[EMAIL disabled] to={to} subject={subject!r}")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RESEND_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.EMAIL_FROM,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
        if resp.status_code in (200, 201):
            return True
        print(f"[EMAIL error] Resend returned {resp.status_code}: {resp.text[:300]}")
        return False
    except httpx.HTTPError as exc:
        print(f"[EMAIL error] {exc}")
        return False
