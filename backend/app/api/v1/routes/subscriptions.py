from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.subscription import PlanResponse, SubscriptionResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import User
from app.services.subscription import get_tenant_subscription, list_active_plans

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=list[PlanResponse])
async def plans(db: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    return [PlanResponse.model_validate(plan, from_attributes=True) for plan in await list_active_plans(db)]


@router.get("/{tenant_public_id}", response_model=SubscriptionResponse)
async def current_subscription(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SubscriptionResponse:
    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return SubscriptionResponse(
        public_id=subscription.public_id,
        status=subscription.status,
        billing_interval=subscription.billing_interval,
        starts_at=subscription.starts_at,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        plan=PlanResponse.model_validate(subscription.plan, from_attributes=True),
    )
