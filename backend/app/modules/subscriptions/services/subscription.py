import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now
from app.modules.auth.models.identity import User
from app.modules.subscriptions.models.subscription import Plan, Subscription, SubscriptionEvent
from app.modules.tenancy.models.tenant import Tenant, TenantUser

# Canonical subscription statuses.
STATUS_TRIAL = "trial"
STATUS_ACTIVE = "active"
STATUS_PAST_DUE = "past_due"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"

VALID_STATUSES = {
    STATUS_TRIAL,
    STATUS_ACTIVE,
    STATUS_PAST_DUE,
    STATUS_CANCELLED,
    STATUS_EXPIRED,
}

# Allowed transitions: from_status -> set of target statuses.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    STATUS_TRIAL: {STATUS_ACTIVE, STATUS_CANCELLED, STATUS_EXPIRED, STATUS_TRIAL},
    STATUS_ACTIVE: {STATUS_PAST_DUE, STATUS_CANCELLED, STATUS_EXPIRED, STATUS_ACTIVE, STATUS_TRIAL},
    STATUS_PAST_DUE: {STATUS_ACTIVE, STATUS_CANCELLED, STATUS_EXPIRED},
    STATUS_CANCELLED: {STATUS_EXPIRED},
    STATUS_EXPIRED: set(),  # terminal
}

VALID_INTERVALS = {
    "monthly": "monthly_price_minor",
    "quarterly": "quarterly_price_minor",
    "yearly": "yearly_price_minor",
}

INTERVAL_DAYS = {"monthly": 30, "quarterly": 90, "yearly": 365}

# Statuses that still grant plan entitlements.
ENTITLED_STATUSES = {STATUS_TRIAL, STATUS_ACTIVE, STATUS_PAST_DUE}


def _assert_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invalid_subscription_transition",
                "from_status": current,
                "to_status": target,
            },
        )


def _add_event(
    db: AsyncSession,
    subscription_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> SubscriptionEvent:
    event = SubscriptionEvent(
        public_id=uuid.uuid4().hex,
        subscription_id=subscription_id,
        event_type=event_type,
        payload=payload or {},
    )
    db.add(event)
    return event


async def list_active_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.features))
        .where(Plan.is_active.is_(True))
        .order_by(Plan.monthly_price_minor, Plan.name)
    )
    return list(result.scalars().unique().all())


async def get_tenant_subscription(
    db: AsyncSession, user: User, tenant_public_id: str
) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan).selectinload(Plan.features))
        .join(Tenant, Tenant.id == Subscription.tenant_id)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            Tenant.public_id == tenant_public_id,
            TenantUser.user_id == user.id,
            TenantUser.status == "active",
        )
    )
    return result.scalar_one_or_none()


def interval_end(start: datetime, interval: str, trial_days: int = 0) -> datetime:
    days = INTERVAL_DAYS.get(interval)
    if days is None:
        raise HTTPException(status_code=422, detail="Invalid billing interval")
    return start + timedelta(days=days + trial_days)


def is_entitled(subscription: Subscription) -> bool:
    """Whether the subscription currently grants plan features."""
    if subscription.status not in ENTITLED_STATUSES:
        return False
    if subscription.current_period_end is None:
        return True
    return subscription.current_period_end >= utc_now()


async def change_subscription(
    db: AsyncSession,
    user: User,
    tenant_public_id: str,
    plan_public_id: str,
    billing_interval: str,
) -> Subscription:
    if billing_interval not in VALID_INTERVALS:
        raise HTTPException(status_code=422, detail="Invalid billing interval")

    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.status in {STATUS_CANCELLED, STATUS_EXPIRED}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "subscription_not_modifiable",
                "status": subscription.status,
                "message": "Cancelled or expired subscriptions require a new billing flow",
            },
        )

    plan = await db.scalar(
        select(Plan)
        .options(selectinload(Plan.features))
        .where(Plan.public_id == plan_public_id, Plan.is_active.is_(True))
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    price_attr = VALID_INTERVALS[billing_interval]
    if getattr(plan, price_attr) > 0:
        raise HTTPException(
            status_code=409,
            detail="Paid plan changes require the payment flow",
        )

    old_plan_slug = subscription.plan.slug
    old_status = subscription.status
    new_status = STATUS_TRIAL if plan.trial_days > 0 else STATUS_ACTIVE
    _assert_transition(old_status, new_status)

    subscription.plan_id = plan.id
    subscription.billing_interval = billing_interval
    subscription.status = new_status
    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None
    start = utc_now()
    subscription.starts_at = start
    subscription.current_period_end = interval_end(start, billing_interval, plan.trial_days)

    _add_event(
        db,
        subscription.id,
        "subscription.plan_changed",
        {
            "from_plan": old_plan_slug,
            "to_plan": plan.slug,
            "billing_interval": billing_interval,
            "from_status": old_status,
            "to_status": new_status,
            "actor_user_id": user.id,
        },
    )
    await db.flush()
    return subscription


async def cancel_subscription(
    db: AsyncSession, user: User, tenant_public_id: str, immediately: bool
) -> Subscription:
    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.status in {STATUS_CANCELLED, STATUS_EXPIRED}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "subscription_already_ended",
                "status": subscription.status,
            },
        )

    now = utc_now()
    old_status = subscription.status

    if immediately:
        _assert_transition(old_status, STATUS_CANCELLED)
        subscription.status = STATUS_CANCELLED
        subscription.cancelled_at = now
        subscription.cancel_at_period_end = False
        event_type = "subscription.cancelled"
    else:
        # Schedule cancellation at period end; keep current entitled status.
        subscription.cancel_at_period_end = True
        event_type = "subscription.cancel_scheduled"

    _add_event(
        db,
        subscription.id,
        event_type,
        {
            "immediately": immediately,
            "from_status": old_status,
            "to_status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "actor_user_id": user.id,
        },
    )
    await db.flush()
    return subscription


async def reactivate_subscription(
    db: AsyncSession, user: User, tenant_public_id: str
) -> Subscription:
    subscription = await get_tenant_subscription(db, user, tenant_public_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.status in {STATUS_CANCELLED, STATUS_EXPIRED}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "subscription_requires_new_billing",
                "status": subscription.status,
                "message": "Cancelled or expired subscriptions require a new billing flow",
            },
        )

    if not subscription.cancel_at_period_end:
        # Already active with no pending cancellation — idempotent success.
        return subscription

    old_status = subscription.status
    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None

    _add_event(
        db,
        subscription.id,
        "subscription.reactivated",
        {
            "from_status": old_status,
            "to_status": subscription.status,
            "actor_user_id": user.id,
        },
    )
    await db.flush()
    return subscription


async def expire_due_subscriptions(db: AsyncSession, *, batch_size: int = 200) -> int:
    """Expire subscriptions that have passed their period end.

    Rules:
    - cancel_at_period_end=True  -> cancelled
    - otherwise (trial/active/past_due past end) -> expired

    Returns the number of subscriptions updated.
    """
    now = utc_now()
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.status.in_([STATUS_TRIAL, STATUS_ACTIVE, STATUS_PAST_DUE]),
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end <= now,
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    subscriptions = list(result.scalars().all())
    if not subscriptions:
        return 0

    updated = 0
    for sub in subscriptions:
        old_status = sub.status
        if sub.cancel_at_period_end:
            target = STATUS_CANCELLED
            event_type = "subscription.cancelled_at_period_end"
            sub.cancelled_at = now
            sub.cancel_at_period_end = False
        else:
            target = STATUS_EXPIRED
            event_type = "subscription.expired"

        # Skip if transition is not allowed (defensive).
        if target not in ALLOWED_TRANSITIONS.get(old_status, set()):
            continue

        sub.status = target
        _add_event(
            db,
            sub.id,
            event_type,
            {
                "from_status": old_status,
                "to_status": target,
                "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "source": "maintenance_worker",
            },
        )
        updated += 1

    if updated:
        await db.flush()
    return updated
