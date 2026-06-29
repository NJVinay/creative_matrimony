"""
Notification Service.
Trace: @context_documents/MVP_BACKLOG.md Epic K
"""

from typing import List, Optional, Any, Dict
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType

class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: int,
        type: NotificationType,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            data=data
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Notification]:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: int, user_id: int):
        await db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        await db.commit()

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int):
        await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await db.commit()
