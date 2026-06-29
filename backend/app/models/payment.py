"""
Payment models — Subscription Plans, User Subscriptions, and Transactions.
Trace: @context_documents/IDEA_PLANNER.md §6
"""

from datetime import datetime
import enum

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Float, JSON, func
)
from app.database import Base


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    refunded = "refunded"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # e.g., "Gold", "Diamond"
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    duration_days = Column(Integer, nullable=False)
    features = Column(JSON, nullable=True)  # List of features for UI
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    payment_transaction_id = Column(Integer, ForeignKey("payment_transactions.id"), nullable=True)
    
    start_date = Column(DateTime, server_default=func.now(), nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    
    provider = Column(String(50), default="mock")  # razorpay, stripe, mock
    provider_order_id = Column(String(100), nullable=True, index=True)
    provider_payment_id = Column(String(100), nullable=True, index=True)
    provider_signature = Column(String(200), nullable=True)
    
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending)
    error_details = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
