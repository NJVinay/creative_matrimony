"""
Weekly Digest Worker
Trace: @context_documents/MVP_BACKLOG.md Epic G2

This is a standalone async script intended to be run periodically via a system Cron job
or an orchestrator like GitHub Actions. It calculates matches and dispatches "mock" emails.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Ensure the backend directory is in the path for module loading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import async_session_maker
from app.models.user import User
from app.models.profile import Profile
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType

async def dispatch_digest_email(user: User, recommendations: list):
    """Mock dispatcher for sending the weekly digest email."""
    if not recommendations:
        return

    print(f"\n{'='*50}")
    print(f"  [MOCK EMAIL DISPATCH] TO: {user.phone} / {user.email}")
    print(f"  SUBJECT: Your Weekly Matches on Creative Matrimony")
    print(f"  BODY: We found {len(recommendations)} highly compatible matches for you!")
    for idx, (prof, score) in enumerate(recommendations, 1):
        print(f"    {idx}. Match Score {score}: Profile ID {prof.id}")
    print(f"{'='*50}\n")


async def run_weekly_digest():
    print(f"Starting Weekly Digest Worker at {datetime.now(timezone.utc)}")
    
    async with async_session_maker() as db:
        offset = 0
        limit = 100
        count = 0
        
        while True:
            # Fetch users in batches
            result = await db.execute(
                select(User)
                .where(User.is_banned == False)
                .options(selectinload(User.profile))
                .order_by(User.id)
                .offset(offset)
                .limit(limit)
            )
            users = result.scalars().all()
            
            if not users:
                break
                
            for user in users:
                if not user.profile:
                    continue
                    
                try:
                    # For MVP, we'll just pull the top 3 recommendations
                    recommendations = await MatchingService.get_recommendations(db, user.profile.id, limit=3)
                    
                    if recommendations:
                        # Dispatch Email
                        await dispatch_digest_email(user, recommendations)
                        
                        # Create an in-app notification
                        await NotificationService.create_notification(
                            db=db,
                            user_id=user.id,
                            type=NotificationType.system,
                            title="Your Weekly Matches are here!",
                            body=f"We found {len(recommendations)} new matches based on your preferences.",
                            data={"count": len(recommendations)}
                        )
                        count += 1
                except Exception as e:
                    print(f"Error processing weekly digest for user {user.id}: {e}")
                    # Continue processing remaining users
                    continue
            
            offset += limit
            
        await db.commit()
        print(f"Successfully processed {count} weekly digests.")

if __name__ == "__main__":
    asyncio.run(run_weekly_digest())
