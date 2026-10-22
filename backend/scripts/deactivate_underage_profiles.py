"""
Deactivate and hide legacy profiles below the legal marriage age
(18 for women, 21 for men and others), created before the DOB check existed,
and cut them off from other members: their open chat rooms are closed and
their pending interests (sent or received) are cancelled.

Usage — run from a folder whose .env points at the INTENDED database
(normally backend/). DATABASE_URL is read from the environment / ./.env
exactly like the app, so check the "Database:" line before applying:

    python scripts/deactivate_underage_profiles.py            # dry run: report only
    python scripts/deactivate_underage_profiles.py --apply    # write the changes below

--apply sets is_active=False and visibility=hidden on the profiles, sets
is_active=False on every chat room their users take part in, and sets their
pending interests (both directions) to cancelled.

Safe to re-run: rows already in that state are left alone, and no row is
ever deleted. Output lists profile id, age and gender, and counts of rooms
and interests (no names, phone numbers or message content).
"""

import argparse
import asyncio
import pathlib
import sys
from dataclasses import dataclass, field

# Make `app` importable when run as a plain script (python scripts/...)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import not_, or_, select, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.models  # noqa: E402,F401 — register all tables/relationships
from app.models.communication import ChatParticipant, ChatRoom, Interest, InterestStatus  # noqa: E402
from app.models.profile import Profile, Visibility  # noqa: E402
from app.services.profile_service import calculate_age, legal_age_condition  # noqa: E402


@dataclass
class UnderageProfile:
    id: int
    age: int
    gender: str
    needs_update: bool  # still active or not hidden


@dataclass
class CleanupReport:
    profiles: list[UnderageProfile] = field(default_factory=list)
    updated: int = 0  # profiles changed by this run (0 on a dry run)
    open_chat_rooms: int = 0  # active rooms any of them takes part in
    pending_interests: int = 0  # pending interests sent or received by them
    chat_rooms_closed: int = 0  # changed by this run (0 on a dry run)
    interests_cancelled: int = 0  # changed by this run (0 on a dry run)


async def deactivate_underage_profiles(session: AsyncSession, *, apply: bool = False) -> CleanupReport:
    """Find profiles below the legal marriage age; with apply=True set
    is_active=False and visibility=hidden on those not already so, close the
    chat rooms their users are in and cancel their pending interests, and commit.
    Rooms and interests are handled for every under-age profile, including ones
    already inactive and hidden. Uses the same age rule as discovery
    (legal_age_condition). Never deletes."""
    result = await session.execute(
        select(Profile).where(not_(legal_age_condition())).order_by(Profile.id)
    )
    report = CleanupReport()
    profile_ids: list[int] = []
    user_ids: list[int] = []
    for profile in result.scalars().all():
        needs_update = bool(profile.is_active) or profile.visibility != Visibility.hidden
        report.profiles.append(UnderageProfile(
            id=profile.id,
            age=calculate_age(profile.date_of_birth),
            gender=profile.gender.value if profile.gender else "unknown",
            needs_update=needs_update,
        ))
        if apply and needs_update:
            profile.is_active = False
            profile.visibility = Visibility.hidden
            report.updated += 1
        profile_ids.append(profile.id)
        user_ids.append(profile.user_id)

    if profile_ids:
        room_ids = (await session.scalars(
            select(ChatRoom.id).distinct()
            .join(ChatParticipant, ChatParticipant.room_id == ChatRoom.id)
            .where(ChatParticipant.user_id.in_(user_ids), ChatRoom.is_active.is_(True))
        )).all()
        interest_ids = (await session.scalars(
            select(Interest.id).where(
                or_(Interest.sender_id.in_(profile_ids), Interest.receiver_id.in_(profile_ids)),
                Interest.status == InterestStatus.pending.value,
            )
        )).all()
        report.open_chat_rooms = len(room_ids)
        report.pending_interests = len(interest_ids)
        if apply and room_ids:
            await session.execute(
                update(ChatRoom).where(ChatRoom.id.in_(room_ids)).values(is_active=False)
            )
            report.chat_rooms_closed = len(room_ids)
        if apply and interest_ids:
            await session.execute(
                update(Interest).where(Interest.id.in_(interest_ids))
                .values(status=InterestStatus.cancelled.value)
            )
            report.interests_cancelled = len(interest_ids)

    if apply and (report.updated or report.chat_rooms_closed or report.interests_cancelled):
        await session.commit()
    return report


async def main(apply: bool) -> None:
    from sqlalchemy.engine import make_url
    from app.database import DATABASE_URL, async_session, engine

    print(f"Database: {make_url(DATABASE_URL).render_as_string(hide_password=True)}")
    print("Mode: APPLY (writes changes)" if apply else "Mode: dry run (no changes; pass --apply to write)")
    try:
        async with async_session() as session:
            report = await deactivate_underage_profiles(session, apply=apply)
    finally:
        await engine.dispose()

    pending = sum(p.needs_update for p in report.profiles)
    print(f"Under-age profiles: {len(report.profiles)} ({pending} still active or not hidden)")
    for p in report.profiles:
        state = "" if p.needs_update else "  [already inactive + hidden]"
        print(f"  id={p.id} age={p.age} gender={p.gender}{state}")
    print(f"Open chat rooms with them: {report.open_chat_rooms}")
    print(f"Pending interests sent or received by them: {report.pending_interests}")
    if apply:
        print(f"Updated: {report.updated} profiles, {report.chat_rooms_closed} chat rooms closed, "
              f"{report.interests_cancelled} interests cancelled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="deactivate and hide the profiles (default: dry run)")
    asyncio.run(main(parser.parse_args().apply))
