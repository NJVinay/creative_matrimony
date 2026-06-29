"""
Seed Subscription Plans.
"""
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.payment import SubscriptionPlan

PLANS = [
    {
        "name": "Gold",
        "price": 2999.00,
        "currency": "INR",
        "duration_days": 90,
        "features": ["Unlimited Messaging", "View 50 Phone Numbers", "Priority Support"]
    },
    {
        "name": "Diamond",
        "price": 4999.00,
        "currency": "INR",
        "duration_days": 180,
        "features": ["Unlimited Messaging", "View 150 Phone Numbers", "Dedicated Relationship Manager", "Profile Highlighter"]
    },
    {
        "name": "Till You Marry",
        "price": 9999.00,
        "currency": "INR",
        "duration_days": 365,
        "features": ["Unlimited Everything", "Personal Matchmaker", "Horoscope Matching"]
    }
]

async def seed_plans():
    async with async_session() as db:
        print("Checking subscription plans...")
        result = await db.execute(select(SubscriptionPlan))
        existing = result.scalars().all()
        
        if existing:
            print(f"Found {len(existing)} plans. Skipping seed.")
            return

        print("Seeding plans...")
        for p_data in PLANS:
            plan = SubscriptionPlan(**p_data)
            db.add(plan)
        
        await db.commit()
        print("✅ Plans seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
