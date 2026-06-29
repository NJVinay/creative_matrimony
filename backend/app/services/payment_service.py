"""
Payment Service — Subscription management and Mock Payment Provider.
Trace: @context_documents/MVP_BACKLOG.md Epic H
"""

import hmac
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import SubscriptionPlan, UserSubscription, PaymentTransaction, TransactionStatus
from app.models.user import User

# Mock Provider — signs a deterministic token bound to the order so the
# frontend can recompute it without exposing a real secret.
MOCK_PAYMENT_SECRET = "MOCK_RAZORPAY_SECRET_DO_NOT_USE_IN_PROD"


class PaymentProvider:
    @staticmethod
    def create_order(amount: float, currency: str = "INR") -> dict:
        """Simulate creating an order with a gateway like Razorpay."""
        return {
            "id": f"order_{uuid.uuid4().hex[:10]}",
            "entity": "order",
            "amount": int(amount * 100),  # amounts in paise
            "currency": currency,
            "status": "created",
        }

    @staticmethod
    def sign(order_id: str, payment_id: str) -> str:
        """Deterministic HMAC-SHA256 signature for the mock provider."""
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        return hmac.new(
            MOCK_PAYMENT_SECRET.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify a payment signature.
        The expected signature is HMAC-SHA256(secret, f"{order_id}|{payment_id}").
        Constant-time compare to avoid timing leaks.
        """
        if not signature or not order_id or not payment_id:
            return False
        expected = PaymentProvider.sign(order_id, payment_id)
        try:
            return hmac.compare_digest(expected, signature)
        except (TypeError, AttributeError):
            return False


class PaymentService:
    @staticmethod
    async def get_active_plans(db: AsyncSession) -> List[SubscriptionPlan]:
        result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)))
        plans = result.scalars().all()
        
        if not plans:
            # Seed a default plan for MVP
            plan = SubscriptionPlan(
                name="Premium Match",
                price=999.0,
                duration_days=30,
                features=["Unlimited Messages", "View Contact Info", "Priority Support"]
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return [plan]
            
        return list(plans)

    @staticmethod
    async def create_subscription_order(
        db: AsyncSession, 
        user_id: int, 
        plan_id: int
    ) -> dict:
        """
        1. Fetch plan details
        2. Create transaction record (pending)
        3. Call provider to create order
        4. Return order details to frontend
        """
        # Fetch plan
        plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError("Invalid Plan ID")

        # Create Order on Provider
        provider_order = PaymentProvider.create_order(plan.price)

        # Record Transaction
        txn = PaymentTransaction(
            user_id=user_id,
            subscription_plan_id=plan.id,
            amount=plan.price,
            currency=plan.currency,
            provider="mock",
            provider_order_id=provider_order["id"],
            status=TransactionStatus.pending
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        return {
            "order_id": provider_order["id"],
            "amount": plan.price,
            "currency": plan.currency,
            "key": "mock_key_123" # Public key for frontend
        }

    @staticmethod
    async def activate_subscription(
        db: AsyncSession,
        user_id: int,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str
    ) -> UserSubscription:
        """
        1. Verify signature
        2. Update transaction status
        3. Create UserSubscription
        4. Upgrade User Role (implicitly via active sub)
        """
        # Verify
        if not PaymentProvider.verify_signature(provider_order_id, provider_payment_id, signature):
            raise ValueError("Payment Verification Failed")

        # Find transaction
        result = await db.execute(select(PaymentTransaction).where(
            PaymentTransaction.provider_order_id == provider_order_id
        ))
        txn = result.scalar_one_or_none()
        if not txn:
            raise ValueError("Transaction not found")

        # Update Transaction
        txn.status = TransactionStatus.success
        txn.provider_payment_id = provider_payment_id
        txn.provider_signature = signature
        
        # Get Plan details
        # Reload plan in case it changed, though ID is immutable mostly
        plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == txn.subscription_plan_id))
        plan = plan_result.scalar_one()

        # Create Subscription
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        # Deactivate old subscriptions
        await db.execute(
            update(UserSubscription)
            .where(UserSubscription.user_id == user_id, UserSubscription.is_active.is_(True))
            .values(is_active=False)
        )

        new_sub = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            payment_transaction_id=txn.id,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        db.add(new_sub)
        
        await db.commit()
        await db.refresh(new_sub)
        return new_sub

    @staticmethod
    async def activate_trial(db: AsyncSession, user_id: int) -> UserSubscription:
        """Instantly grant a 30-day Premium trial to the user."""
        # Deactivate old subscriptions
        await db.execute(
            update(UserSubscription)
            .where(UserSubscription.user_id == user_id, UserSubscription.is_active.is_(True))
            .values(is_active=False)
        )
        
        # We need a plan ID for the trial. Just grab the first active plan (e.g. Premium Match)
        plans = await PaymentService.get_active_plans(db)
        if not plans:
            raise ValueError("No subscription plans available for trial")
            
        plan_id = plans[0].id
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30)
        
        trial_sub = UserSubscription(
            user_id=user_id,
            plan_id=plan_id,
            payment_transaction_id=None, # No transaction for free trial
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        db.add(trial_sub)
        await db.commit()
        await db.refresh(trial_sub)
        return trial_sub
