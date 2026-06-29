"""
Chat Service.
Trace: @context_documents/MVP_BACKLOG.md Epic G
"""

import re
from typing import List, Optional
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.communication import Interest, InterestStatus, ChatRoom, ChatParticipant, ChatMessage
from app.models.user import User
from app.models.profile import Profile
from app.models.notification import NotificationType
from app.services.notification_service import NotificationService

class ChatService:
    # ── Interest Management ────────────────────────────────────
    
    @staticmethod
    async def send_interest(db: AsyncSession, sender_id: int, receiver_id: int) -> Interest:
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
        user_id is the action performer. 
        Only receiver can accept/reject. Sender can cancel? (Scope: MVP receiver only)
        """
        result = await db.execute(
            select(Interest).where(Interest.id == interest_id, Interest.receiver_id == user_id)
        )
        interest = result.scalar_one_or_none()
        if not interest:
            return None
            
        interest.status = status
        
        # Logic: If Accepted -> Create ChatRoom
        if status == InterestStatus.accepted:
            # Check if room already exists? (Maybe they re-matched)
            # For MVP assume new room
            room = ChatRoom(is_active=True)
            db.add(room)
            await db.flush() # get ID
            
            # Add participants (Link to USER IDs, not Profile IDs. Wait, Profile is 1-to-1 with User)
            # My Interest model stores Profile IDs. ChatParticipant stores User IDs.
            # I need to fetch User IDs from Profile IDs.
            # Assuming Profile.user_id exists.
            
            # Since I don't have Profile loaded with user relation here easily, I'll trust Profile.user_id via query or fetch
            # Actually ChatParticipant links to User. Interest links to Profile.
            # Profile has a 'user_id' column.
            
            # Let's fetch profile data to get user_ids
            from app.models.profile import Profile
            p1 = (await db.execute(select(Profile).where(Profile.id == interest.sender_id))).scalar_one()
            p2 = (await db.execute(select(Profile).where(Profile.id == interest.receiver_id))).scalar_one()
            
            part1 = ChatParticipant(room_id=room.id, user_id=p1.user_id)
            part2 = ChatParticipant(room_id=room.id, user_id=p2.user_id)
            db.add_all([part1, part2])
            
            # Notify the sender that their interest was accepted
            await NotificationService.create_notification(
                db=db,
                user_id=p1.user_id,
                type=NotificationType.interest,
                title="Interest Accepted",
                body="Your interest was accepted! A new chat room has been created.",
                data={"interest_id": interest.id, "room_id": room.id}
            )
            
        await db.commit()
        await db.refresh(interest)
        return interest

    # ── Chat Management ────────────────────────────────────────

    @staticmethod
    async def get_user_chats(db: AsyncSession, user_id: int) -> List[ChatRoom]:
        """Get all active chat rooms for a user with latest message preview."""
        # Setup: Find rooms where user is participant
        stmt = select(ChatRoom).join(ChatParticipant).where(
            ChatParticipant.user_id == user_id,
            ChatRoom.is_active == True
        ).options(
            selectinload(ChatRoom.participants).selectinload(ChatParticipant.user).selectinload(User.profile),
            selectinload(ChatRoom.messages) # optimize: limit 1 desc? naive for MVP
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_chat_history(db: AsyncSession, room_id: int, user_id: int, limit: int = 50) -> List[ChatMessage]:
        # Validate participation
        check = await db.execute(
            select(ChatParticipant).where(ChatParticipant.room_id == room_id, ChatParticipant.user_id == user_id)
        )
        if not check.scalar_one_or_none():
            return [] # or error
            
        stmt = select(ChatMessage).where(ChatMessage.room_id == room_id)\
            .order_by(ChatMessage.created_at.asc()) # .desc() + reverse in UI? asc is easier for log
            
        result = await db.execute(stmt)
        return result.scalars().all()

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

        # Chat Moderation (Regex)
        email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
        phone_pattern = re.compile(r"\b\d{10,12}\b")
        abusive_terms = ["abuse", "harass", "hateword1", "hateword2", "doxx"] # Basic blacklist
        
        lower_content = content.lower()
        if email_pattern.search(content) or phone_pattern.search(content):
            raise ValueError("Message blocked: Sharing contact information (email/phone) is not allowed before mutual consent or via chat. Please keep conversations on the platform.")
        
        if any(term in lower_content for term in abusive_terms):
            raise ValueError("Message blocked: Your message contains language that violates our community guidelines.")

        msg = ChatMessage(room_id=room_id, sender_id=sender_id, content=content)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg
