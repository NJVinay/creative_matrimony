"""
Safety service — panic block logic shared by profile/chat/matching layers.
Trace: @context_documents/SAFETY_TRUST_PLANNER.md,
       @context_documents/MVP_BACKLOG.md Epic J
"""

from sqlalchemy import select, or_, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.safety import UserBlock
from app.models.communication import (
    Interest, InterestStatus, ChatRoom, ChatParticipant,
)
from app.models.profile import Profile


async def are_blocked(db: AsyncSession, user_a: int, user_b: int) -> bool:
    """True when a block exists between the two users, in either direction."""
    result = await db.scalar(
        select(UserBlock).where(
            or_(
                and_(UserBlock.blocker_user_id == user_a, UserBlock.blocked_user_id == user_b),
                and_(UserBlock.blocker_user_id == user_b, UserBlock.blocked_user_id == user_a),
            )
        ).limit(1)
    )
    return result is not None


async def get_blocked_user_ids(db: AsyncSession, user_id: int) -> set[int]:
    """All user ids blocked by, or blocking, the given user (one query)."""
    rows = await db.execute(
        select(UserBlock.blocker_user_id, UserBlock.blocked_user_id).where(
            or_(UserBlock.blocker_user_id == user_id, UserBlock.blocked_user_id == user_id)
        )
    )
    return {blocked if blocker == user_id else blocker for blocker, blocked in rows.all()}


async def block_user(db: AsyncSession, blocker_user_id: int, blocked_user_id: int,
                     reason: str | None = None) -> UserBlock:
    """Panic block: records the block, closes shared chat rooms, and declines
    any pending interests between the two users. Idempotent."""
    existing = await db.scalar(
        select(UserBlock).where(
            UserBlock.blocker_user_id == blocker_user_id,
            UserBlock.blocked_user_id == blocked_user_id,
        )
    )
    if existing:
        return existing

    block = UserBlock(
        blocker_user_id=blocker_user_id,
        blocked_user_id=blocked_user_id,
        reason=reason,
    )
    db.add(block)

    # Close any shared chat rooms
    my_rooms = select(ChatParticipant.room_id).where(ChatParticipant.user_id == blocker_user_id)
    shared_rooms = (await db.execute(
        select(ChatParticipant.room_id).where(
            ChatParticipant.user_id == blocked_user_id,
            ChatParticipant.room_id.in_(my_rooms),
        )
    )).scalars().all()
    if shared_rooms:
        await db.execute(
            update(ChatRoom).where(ChatRoom.id.in_(shared_rooms)).values(is_active=False)
        )

    # Decline pending interests in both directions (interests link profile ids)
    profile_ids = {}
    for uid in (blocker_user_id, blocked_user_id):
        pid = await db.scalar(select(Profile.id).where(Profile.user_id == uid))
        profile_ids[uid] = pid
    p1, p2 = profile_ids[blocker_user_id], profile_ids[blocked_user_id]
    if p1 and p2:
        await db.execute(
            update(Interest)
            .where(
                or_(
                    and_(Interest.sender_id == p1, Interest.receiver_id == p2),
                    and_(Interest.sender_id == p2, Interest.receiver_id == p1),
                ),
                Interest.status == InterestStatus.pending,
            )
            .values(status=InterestStatus.rejected)
        )

    await db.flush()
    return block


async def unblock_user(db: AsyncSession, blocker_user_id: int, blocked_user_id: int) -> bool:
    """Remove a block the caller created. Returns True if one was removed."""
    existing = await db.scalar(
        select(UserBlock).where(
            UserBlock.blocker_user_id == blocker_user_id,
            UserBlock.blocked_user_id == blocked_user_id,
        )
    )
    if not existing:
        return False
    await db.delete(existing)
    await db.flush()
    return True
