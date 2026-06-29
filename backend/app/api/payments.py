"""
Payment API — Plans and Checkout.
Trace: @context_documents/MVP_BACKLOG.md Epic H
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])

# Schemas
class PlanOut(BaseModel):
    id: int
    name: str # Corrected from 'string'
    price: float
    currency: str
    duration_days: int
    features: List[str]

class CreateOrderRequest(BaseModel):
    plan_id: int

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: float
    currency: str
    key: str

class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

class VerifyPaymentResponse(BaseModel):
    status: str
    subscription_id: int

class MockSignRequest(BaseModel):
    order_id: str
    payment_id: str

class SubscriptionOut(BaseModel):
    id: int
    plan_id: int
    is_active: bool
    end_date: str
    
    model_config = {"from_attributes": True}


@router.get("/plans", response_model=List[PlanOut])
async def list_plans(db: Annotated[AsyncSession, Depends(get_db)]):
    """List all active subscription plans."""
    return await PaymentService.get_active_plans(db)


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    body: CreateOrderRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start checkout flow."""
    try:
        return await PaymentService.create_subscription_order(db, user.id, body.plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    body: VerifyPaymentRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Complete checkout flow."""
    try:
        sub = await PaymentService.activate_subscription(
            db, user.id, body.order_id, body.payment_id, body.signature
        )
        return {"status": "success", "subscription_id": sub.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/mock/sign")
async def mock_sign(body: MockSignRequest):
    """Generate a valid mock signature for testing the UI."""
    from app.services.payment_service import PaymentProvider
    return {"signature": PaymentProvider.sign(body.order_id, body.payment_id)}

@router.post("/trial")
async def activate_trial(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Activate 30-day Premium Trial."""
    try:
        sub = await PaymentService.activate_trial(db, user.id)
        return {"status": "success", "subscription_id": sub.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

from sqlalchemy import select
from app.models.payment import UserSubscription

@router.get("/my-subscription", response_model=SubscriptionOut | None)
async def get_my_subscription(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current active subscription if any."""
    result = await db.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user.id, UserSubscription.is_active.is_(True))
    )
    sub = result.scalar_one_or_none()
    
    if not sub:
        return None
        
    return SubscriptionOut(
        id=sub.id,
        plan_id=sub.plan_id,
        is_active=sub.is_active,
        end_date=sub.end_date.isoformat()
    )
