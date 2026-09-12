import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from app.modules.subscriptions.schemas import subscription
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import ensure_utc, utc_now
from app.modules.auth.models.identity import User
from app.modules.subscriptions.models.subscription import (
    Plan,
    Subscription,
    SubscriptionEvent,
)
from app.modules.tenancy.models.tenant import Tenant, TenantUser

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

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    STATUS_TRIAL: {STATUS_ACTIVE, STATUS_CANCELLED, STATUS_EXPIRED, STATUS_TRIAL},
    STATUS_ACTIVE: {
        STATUS_PAST_DUE,
        STATUS_CANCELLED,
        STATUS_EXPIRED,
        STATUS_ACTIVE,
        STATUS_TRIAL,
    },
    STATUS_PAST_DUE: {STATUS_ACTIVE, STATUS_CANCELLED, STATUS_EXPIRED},
    STATUS_CANCELLED: {STATUS_EXPIRED},
    STATUS_EXPIRED: set(),
}

VALID_INTERVALS = ("monthly", "quarterly", "yearly")

ENTITLED_STATUSES = {STATUS_TRIAL, STATUS_ACTIVE, STATUS_PAST_DUE}


def _interval_days(interval: str) -> int:
    mapping = {
        "monthly": settings.billing_interval_days_monthly,
        "quarterly": settings.billing_interval_days_quarterly,
        "yearly": settings.billing_interval_days_yearly,
    }
    if interval not in mapping:
        raise HTTPException(status_code=422, detail="Invalid billing interval")
    return mapping[interval]


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


def interval_end(start: datetime, interval: str, trial_days: int = 0) -> datetime:
    return start + timedelta(days=_interval_days(interval) + max(trial_days, 0))


def is_entitled(subscription: Subscription) -> bool:
    if subscription.status not in ENTITLED_STATUSES:
        return False
    if subscription.current_period_end is None:
        return True
    return ensure_utc(subscription.current_period_end) >= utc_now()

async def list_active_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.features))
        .where(Plan.is_active.is_(True))
        .order_by(Plan.sort_order, Plan.monthly_price_minor, Plan.name)
    )
    return list(result.scalars().unique().all())


async def list_public_plans(db: AsyncSession) -> list[Plan]:
    """Plans safe for the public landing / pricing page."""
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.features))
        .where(Plan.is_active.is_(True), Plan.is_public.is_(True))
        .order_by(Plan.sort_order, Plan.monthly_price_minor, Plan.name)
    )
    return list(result.scalars().unique().all())


async def get_public_plan_by_slug(db: AsyncSession, slug: str) -> Plan | None:
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.features))
        .where(
            Plan.slug == slug,
            Plan.is_active.is_(True),
            Plan.is_public.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_plan_by_public_id(db: AsyncSession, public_id: str) -> Plan | None:
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.features))
        .where(Plan.public_id == public_id, Plan.is_active.is_(True))
    )
    return result.scalar_one_or_none()


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


async def list_subscription_events(
    db: AsyncSession, subscription_id: int, *, limit: int = 50
) -> list[SubscriptionEvent]:
    result = await db.execute(
        select(SubscriptionEvent)
        .where(SubscriptionEvent.subscription_id == subscription_id)
        .order_by(SubscriptionEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


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

    plan = await get_plan_by_public_id(db, plan_public_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Paid changes are gated until the payment provider flow is wired.
    if plan.price_for_interval(billing_interval) > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "payment_required",
                "message": "Paid plan changes require the payment flow",
                "plan_public_id": plan.public_id,
                "billing_interval": billing_interval,
                "amount_minor": plan.price_for_interval(billing_interval),
                "currency": plan.currency,
            },
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

    # Ensure relationship reflects the new plan for response serialization.
    subscription.plan = plan

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
                "period_end": (
                    sub.current_period_end.isoformat() if sub.current_period_end else None
                ),
                "source": "maintenance_worker",
            },
        )
        updated += 1

    if updated:
        await db.flush()
    return updated
