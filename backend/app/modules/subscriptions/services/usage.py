from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.modules.subscriptions.entitlements import feature_limit, is_subscription_entitled
from app.modules.subscriptions.models.billing import UsageMeter
from app.modules.subscriptions.models.subscription import Subscription


def period_key_for(now: datetime | None = None) -> str:
    """Calendar month period key used for metered features (YYYY-MM)."""
    ts = now or utc_now()
    return ts.strftime("%Y-%m")


async def get_usage(
    db: AsyncSession,
    tenant_id: int,
    feature_key: str,
    *,
    period_key: str | None = None,
) -> int:
    key = period_key or period_key_for()
    quantity = await db.scalar(
        select(UsageMeter.quantity).where(
            UsageMeter.tenant_id == tenant_id,
            UsageMeter.feature_key == feature_key,
            UsageMeter.period_key == key,
        )
    )
    return int(quantity or 0)


async def record_usage(
    db: AsyncSession,
    tenant_id: int,
    feature_key: str,
    *,
    delta: int = 1,
    period_key: str | None = None,
) -> int:
    if delta == 0:
        return await get_usage(db, tenant_id, feature_key, period_key=period_key)
    key = period_key or period_key_for()
    meter = await db.scalar(
        select(UsageMeter)
        .where(
            UsageMeter.tenant_id == tenant_id,
            UsageMeter.feature_key == feature_key,
            UsageMeter.period_key == key,
        )
        .with_for_update()
    )
    if meter is None:
        meter = UsageMeter(
            tenant_id=tenant_id,
            feature_key=feature_key,
            period_key=key,
            quantity=max(delta, 0),
        )
        db.add(meter)
    else:
        meter.quantity = max(meter.quantity + delta, 0)
        meter.updated_at = utc_now()
    await db.flush()
    return meter.quantity


async def set_usage(
    db: AsyncSession,
    tenant_id: int,
    feature_key: str,
    quantity: int,
    *,
    period_key: str | None = None,
) -> int:
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    key = period_key or period_key_for()
    meter = await db.scalar(
        select(UsageMeter)
        .where(
            UsageMeter.tenant_id == tenant_id,
            UsageMeter.feature_key == feature_key,
            UsageMeter.period_key == key,
        )
        .with_for_update()
    )
    if meter is None:
        meter = UsageMeter(
            tenant_id=tenant_id,
            feature_key=feature_key,
            period_key=key,
            quantity=quantity,
        )
        db.add(meter)
    else:
        meter.quantity = quantity
        meter.updated_at = utc_now()
    await db.flush()
    return meter.quantity


async def require_usage_within_limit(
    db: AsyncSession,
    subscription: Subscription,
    feature_key: str,
    *,
    additional: int = 1,
    period_key: str | None = None,
) -> int:
    """Raise 403 if current usage + additional would exceed plan limit.

    Returns current usage quantity.
    """
    if not is_subscription_entitled(subscription):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_inactive",
                "status": getattr(subscription, "status", None),
            },
        )
    limit = feature_limit(subscription, feature_key)
    current = await get_usage(
        db, subscription.tenant_id, feature_key, period_key=period_key
    )
    if limit is not None and current + additional > limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_limit_reached",
                "feature": feature_key,
                "limit": limit,
                "current": current,
            },
        )
    return current


async def usage_snapshot(
    db: AsyncSession,
    tenant_id: int,
    feature_keys: list[str],
    *,
    period_key: str | None = None,
) -> dict[str, int]:
    key = period_key or period_key_for()
    result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.tenant_id == tenant_id,
            UsageMeter.feature_key.in_(feature_keys),
            UsageMeter.period_key == key,
        )
    )
    meters = {m.feature_key: m.quantity for m in result.scalars().all()}
    return {fk: int(meters.get(fk, 0)) for fk in feature_keys}
