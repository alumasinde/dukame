import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import utc_now
from app.models.identity import Tenant, TenantUser, User
from app.models.subscription import Plan, Subscription, SubscriptionEvent

VALID_INTERVALS = {"monthly": "monthly_price_minor", "quarterly": "quarterly_price_minor", "yearly": "yearly_price_minor"}


async def list_active_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).options(selectinload(Plan.features)).where(Plan.is_active.is_(True)).order_by(Plan.monthly_price_minor, Plan.name))
    return list(result.scalars().unique().all())


async def get_tenant_subscription(db: AsyncSession, user: User, tenant_public_id: str) -> Subscription | None:
    result = await db.execute(select(Subscription).options(selectinload(Subscription.plan).selectinload(Plan.features)).join(Tenant, Tenant.id == Subscription.tenant_id).join(TenantUser, TenantUser.tenant_id == Tenant.id).where(Tenant.public_id == tenant_public_id, TenantUser.user_id == user.id, TenantUser.status == "active"))
    return result.scalar_one_or_none()


def interval_end(start, interval: str, trial_days: int = 0):
    return start + timedelta(days={"monthly": 30, "quarterly": 90, "yearly": 365}[interval] + trial_days)


async def change_subscription(db: AsyncSession, user: User, tenant_public_id: str, plan_public_id: str, billing_interval: str) -> Subscription:
    if billing_interval not in VALID_INTERVALS:
        raise HTTPException(status_code=422, detail="Invalid billing interval")
    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    plan = await db.scalar(select(Plan).options(selectinload(Plan.features)).where(Plan.public_id == plan_public_id, Plan.is_active.is_(True)))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if getattr(plan, VALID_INTERVALS[billing_interval]) > 0:
        raise HTTPException(status_code=409, detail="Paid plan changes require the payment flow")
    old_plan = subscription.plan.slug
    subscription.plan_id = plan.id
    subscription.billing_interval = billing_interval
    subscription.status = "trial" if plan.trial_days > 0 else "active"
    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None
    start = utc_now()
    subscription.starts_at = start
    subscription.current_period_end = interval_end(start, billing_interval, plan.trial_days)
    db.add(SubscriptionEvent(public_id=uuid.uuid4().hex, subscription_id=subscription.id, event_type="subscription.plan_changed", payload={"from_plan": old_plan, "to_plan": plan.slug, "billing_interval": billing_interval}))
    await db.flush()
    return subscription


async def cancel_subscription(db: AsyncSession, user: User, tenant_public_id: str, immediately: bool) -> Subscription:
    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    now = utc_now()
    if immediately:
        subscription.status = "cancelled"
        subscription.cancelled_at = now
        subscription.cancel_at_period_end = False
    else:
        subscription.cancel_at_period_end = True
    db.add(SubscriptionEvent(public_id=uuid.uuid4().hex, subscription_id=subscription.id, event_type="subscription.cancelled" if immediately else "subscription.cancel_scheduled", payload={"immediately": immediately}))
    await db.flush()
    return subscription


async def reactivate_subscription(db: AsyncSession, user: User, tenant_public_id: str) -> Subscription:
    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if subscription.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled subscriptions require a new billing flow")
    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None
    db.add(SubscriptionEvent(public_id=uuid.uuid4().hex, subscription_id=subscription.id, event_type="subscription.reactivated", payload={}))
    await db.flush()
    return subscription
