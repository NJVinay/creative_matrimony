"""
Chat Service.
Trace: @context_documents/MVP_BACKLOG.md Epic G
"""

from typing import List, Optional
from sqlalchemy import select, and_, or_, update, not_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.communication import Interest, InterestStatus, ChatRoom, ChatParticipant, ChatMessage
from app.models.user import User
from app.models.profile import Profile
from app.models.notification import NotificationType
from app.services.moderation import check_chat_message
from app.services.notification_service import NotificationService
from app.services.profile_service import check_visibility, legal_age_condition, meets_minimum_age


class InterestAlreadyAnswered(ValueError):
    """The interest was already accepted, declined or cancelled: only a
    pending interest can be answered."""


def can_take_part(profile: Optional[Profile]) -> bool:
    """May this profile send, accept or keep chatting through interests?
    Never below the legal marriage age, and never while deactivated (the
    under-age cleanup deactivates and hides legacy minors)."""
    return (
        profile is not None
        and bool(profile.is_active)
        and meets_minimum_age(profile.date_of_birth, profile.gender)
    )


async def _room_has_underage_participant(db: AsyncSession, room_id: int) -> bool:
    """True when anyone in the room is below the legal marriage age: such a
    room is closed for everyone (not listed, no history, no new messages)."""
    found = await db.scalar(
        select(ChatParticipant.id)
        .join(Profile, Profile.user_id == ChatParticipant.user_id)
        .where(ChatParticipant.room_id == room_id, not_(legal_age_condition()))
        .limit(1)
    )
    return found is not None


class ChatService:
    # ── Interest Management ────────────────────────────────────
    
    @staticmethod
    async def send_interest(db: AsyncSession, sender_id: int, receiver_id: int) -> Interest:
        """Raises LookupError when the receiver does not exist or is below the
        legal marriage age (as if it did not exist, like GET /profiles/{id}),
        ValueError when the interest is not allowed."""
        from app.services.safety_service import are_blocked
        sender = await db.get(Profile, sender_id)
        receiver = await db.get(Profile, receiver_id)
        if receiver is None or not meets_minimum_age(receiver.date_of_birth, receiver.gender):
            raise LookupError("Profile not found.")
        if not can_take_part(sender):
            raise ValueError("Your profile is not active, so you cannot send interests.")
        sender_user = await db.get(User, sender.user_id)
        # Same visibility rule as the profile page (hidden / verified-only),
        # and blocked pairs may not exchange interests (panic block)
        if (
            not receiver.is_active
            or not check_visibility(receiver, sender_user)
            or await are_blocked(db, sender.user_id, receiver.user_id)
        ):
            raise ValueError("You cannot send an interest to this profile.")

        # Check if already exists
        result = await db.execute(
            select(Interest).where(
                Interest.sender_id == sender_id,
                Interest.receiver_id == receiver_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing # or raise error if duplicate sending not allowed
            
        interest = Interest(sender_id=sender_id, receiver_id=receiver_id, status=InterestStatus.pending)
        db.add(interest)
        await db.commit()
        await db.refresh(interest)
        
        # Notify the receiver
        receiver_profile = (await db.execute(select(Profile).where(Profile.id == receiver_id))).scalar_one_or_none()
        if receiver_profile:
            await NotificationService.create_notification(
                db=db,
                user_id=receiver_profile.user_id,
                type=NotificationType.interest,
                title="New Interest Received",
                body="Someone has sent you an interest. Check your pending requests.",
                data={"interest_id": interest.id, "sender_profile_id": sender_id}
            )
            
        return interest

    @staticmethod
    async def get_interests(db: AsyncSession, user_id: int, type: str = "received") -> List[Interest]:
        """type: 'received' or 'sent'"""
        query = select(Interest).options(
            selectinload(Interest.sender), 
            selectinload(Interest.receiver)
        )
        
        if type == "received":
            query = query.where(Interest.receiver_id == user_id)
        else:
            query = query.where(Interest.sender_id == user_id)
            
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_interest_status(db: AsyncSession, interest_id: int, status: InterestStatus, user_id: int) -> Optional[Interest]:
        """
        user_id is the action performer's PROFILE id: only the receiver can
        accept or decline, and only while the interest is pending (raises
        InterestAlreadyAnswered otherwise, also when a parallel request answered
        it first). Accepting opens a chat room, reusing an open one the pair
        already shares. Returns None when there is no such interest for them.
        """
        result = await db.execute(
            select(Interest).where(Interest.id == interest_id, Interest.receiver_id == user_id)
        )
        interest = result.scalar_one_or_none()
        if not interest:
            return None
        if interest.status != InterestStatus.pending:
            raise InterestAlreadyAnswered("This interest has already been answered.")

        # Declining is always allowed. Accepting opens a chat, so both sides
        # must be eligible (legal age, active) and not blocked either way;
        # otherwise the interest is treated as not found (it is not listed).
        sender = await db.get(Profile, interest.sender_id)
        receiver = await db.get(Profile, interest.receiver_id)
        if status == InterestStatus.accepted:
            from app.services.safety_service import are_blocked
            if (
                not can_take_part(sender)
                or not can_take_part(receiver)
                or await are_blocked(db, sender.user_id, receiver.user_id)
            ):
                return None

        # Answer it only if still pending, in one conditional UPDATE, so two
        # parallel answers cannot both go through (e.g. two chat rooms)
        claimed = await db.execute(
            update(Interest)
            .where(Interest.id == interest.id, Interest.status == InterestStatus.pending.value)
            .values(status=status.value)
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            raise InterestAlreadyAnswered("This interest has already been answered.")

        # Logic: If Accepted -> open a chat (ChatParticipant links USER ids;
        # interests link profile ids)
        if status == InterestStatus.accepted:
            # Interests in both directions can be accepted: one room per pair.
            # Lock both profiles (in id order) so accepting both at once cannot
            # open two rooms (PostgreSQL row locks; SQLite serialises writers)
            await db.execute(
                select(Profile.id)
                .where(Profile.id.in_({sender.id, receiver.id}))
                .order_by(Profile.id)
                .with_for_update()
            )
            receiver_rooms = select(ChatParticipant.room_id).where(
                ChatParticipant.user_id == receiver.user_id
            )
            room = await db.scalar(
                select(ChatRoom)
                .join(ChatParticipant, ChatParticipant.room_id == ChatRoom.id)
                .where(
                    ChatParticipant.user_id == sender.user_id,
                    ChatParticipant.room_id.in_(receiver_rooms),
                    ChatRoom.is_active.is_(True),
                )
                .order_by(ChatRoom.id)
                .limit(1)
            )
            if room is None:
                room = ChatRoom(is_active=True)
                db.add(room)
                await db.flush()  # get ID
                db.add_all([
                    ChatParticipant(room_id=room.id, user_id=sender.user_id),
                    ChatParticipant(room_id=room.id, user_id=receiver.user_id),
                ])

            # Notify the sender that their interest was accepted
            await NotificationService.create_notification(
                db=db,
                user_id=sender.user_id,
                type=NotificationType.interest,
                title="Interest Accepted",
                body="Your interest was accepted! You can now chat.",
                data={"interest_id": interest.id, "room_id": room.id}
            )
            
        await db.commit()
        await db.refresh(interest)
        return interest

    # ── Chat Management ────────────────────────────────────────

    @staticmethod
    async def get_user_chats(db: AsyncSession, user_id: int) -> List[ChatRoom]:
        """Get all active chat rooms for a user with latest message preview."""
        # Find rooms where user is a participant; load participants eagerly for display,
        # but DO NOT load messages (would pull entire history of every room).
        stmt = (
            select(ChatRoom)
            .join(ChatParticipant)
            .where(
                ChatParticipant.user_id == user_id,
                ChatRoom.is_active == True,
            )
            .options(
                selectinload(ChatRoom.participants).selectinload(ChatParticipant.user).selectinload(User.profile),
            )
        )

        result = await db.execute(stmt)
        rooms = list(result.scalars().all())

        # Attach a `latest_message` preview per room (one extra query per room is acceptable
        # for inbox rendering; we can replace with a window function later).
        for room in rooms:
            latest = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.room_id == room.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            room.latest_message = latest.scalar_one_or_none()

        return rooms

    @staticmethod
    async def get_chat_history(
        db: AsyncSession, room_id: int, user_id: int, limit: int = 50, offset: int = 0
    ) -> List[ChatMessage]:
        # Validate participation
        check = await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.room_id == room_id, ChatParticipant.user_id == user_id
            )
        )
        if not check.scalar_one_or_none():
            return []
        if await _room_has_underage_participant(db, room_id):
            return []

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at.desc())  # most recent first
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def send_message(db: AsyncSession, room_id: int, sender_id: int, content: str) -> ChatMessage:
        """
        Send a message. Verifies the sender is a participant of the room.
        Raises ValueError if not authorized.
        """
        # Verify participation
        participant_check = await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == sender_id,
            )
        )
        if not participant_check.scalar_one_or_none():
            raise ValueError("Not a participant of this chat room.")

        # Rooms are deactivated when a participant blocks the other (panic block)
        room = (await db.execute(select(ChatRoom).where(ChatRoom.id == room_id))).scalar_one_or_none()
        if not room or not room.is_active or await _room_has_underage_participant(db, room_id):
            raise ValueError("This chat is no longer active.")

        # Chat moderation: contact sharing + abusive language (raises ValueError)
        check_chat_message(content)

        msg = ChatMessage(room_id=room_id, sender_id=sender_id, content=content)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg
