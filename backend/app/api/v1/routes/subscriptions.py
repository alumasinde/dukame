from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.subscription import PlanResponse, SubscriptionCancelRequest, SubscriptionChangeRequest, SubscriptionResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import User
from app.models.subscription import Plan
from app.services.rbac import require_permission
from app.services.subscription_v2 import cancel_subscription, change_subscription, get_tenant_subscription, list_active_plans, reactivate_subscription
from app.services.tenant import get_tenant_by_public_id

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def plan_response(plan: Plan) -> PlanResponse:
    return PlanResponse.model_validate(plan, from_attributes=True)


async def authorized_tenant(db: AsyncSession, user: User, tenant_public_id: str, permission: str):
    tenant = await get_tenant_by_public_id(db, tenant_public_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await require_permission(db, user, tenant.id, permission)
    return tenant


@router.get("/plans", response_model=list[PlanResponse])
async def plans(db: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    return [plan_response(plan) for plan in await list_active_plans(db)]


@router.get("/{tenant_public_id}", response_model=SubscriptionResponse)
async def current_subscription(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return SubscriptionResponse(public_id=subscription.public_id, status=subscription.status, billing_interval=subscription.billing_interval, starts_at=subscription.starts_at, current_period_end=subscription.current_period_end, cancel_at_period_end=subscription.cancel_at_period_end, plan=plan_response(subscription.plan))


@router.get("/{tenant_public_id}/features", response_model=dict[str, Any])
async def features(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.read")
    subscription = await get_tenant_subscription(db, user, tenant.public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {feature.feature_key: feature.value for feature in subscription.plan.features}


@router.post("/{tenant_public_id}/change", response_model=SubscriptionResponse)
async def change(tenant_public_id: str, payload: SubscriptionChangeRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription = await change_subscription(db, user, tenant.public_id, payload.plan_public_id, payload.billing_interval)
    await db.commit()
    return SubscriptionResponse(public_id=subscription.public_id, status=subscription.status, billing_interval=subscription.billing_interval, starts_at=subscription.starts_at, current_period_end=subscription.current_period_end, cancel_at_period_end=subscription.cancel_at_period_end, plan=plan_response(subscription.plan))


@router.post("/{tenant_public_id}/cancel", response_model=SubscriptionResponse)
async def cancel(tenant_public_id: str, payload: SubscriptionCancelRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription = await cancel_subscription(db, user, tenant.public_id, payload.immediately)
    await db.commit()
    return SubscriptionResponse(public_id=subscription.public_id, status=subscription.status, billing_interval=subscription.billing_interval, starts_at=subscription.starts_at, current_period_end=subscription.current_period_end, cancel_at_period_end=subscription.cancel_at_period_end, plan=plan_response(subscription.plan))


@router.post("/{tenant_public_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> SubscriptionResponse:
    tenant = await authorized_tenant(db, user, tenant_public_id, "subscription.manage")
    subscription = await reactivate_subscription(db, user, tenant.public_id)
    await db.commit()
    return SubscriptionResponse(public_id=subscription.public_id, status=subscription.status, billing_interval=subscription.billing_interval, starts_at=subscription.starts_at, current_period_end=subscription.current_period_end, cancel_at_period_end=subscription.cancel_at_period_end, plan=plan_response(subscription.plan))
