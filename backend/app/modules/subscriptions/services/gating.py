"""Plan capacity and entitlement checks used by other modules."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.subscriptions.entitlements import (
    feature_limit,
    is_subscription_entitled,
    require_feature,
    require_within_limit,
)
from app.modules.subscriptions.models.subscription import Plan, Subscription
from app.modules.subscriptions.services.usage import require_usage_within_limit
from app.modules.tenancy.models.tenant import TenantUser


async def get_tenant_subscription_for_gating(
    db: AsyncSession, tenant_id: int
) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan).selectinload(Plan.features))
        .where(Subscription.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def require_active_subscription(
    db: AsyncSession, tenant_id: int
) -> Subscription:
    subscription = await get_tenant_subscription_for_gating(db, tenant_id)
    if subscription is None or not is_subscription_entitled(subscription):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_inactive",
                "status": getattr(subscription, "status", None),
            },
        )
    return subscription


async def count_products_for_tenant(db: AsyncSession, tenant_id: int) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(Product)
        .join(Store, Store.id == Product.store_id)
        .where(Store.tenant_id == tenant_id)
    )
    return int(result or 0)


async def count_stores_for_tenant(db: AsyncSession, tenant_id: int) -> int:
    result = await db.scalar(
        select(func.count()).select_from(Store).where(Store.tenant_id == tenant_id)
    )
    return int(result or 0)


async def count_staff_for_tenant(db: AsyncSession, tenant_id: int) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(TenantUser)
        .where(TenantUser.tenant_id == tenant_id, TenantUser.status == "active")
    )
    return int(result or 0)


async def enforce_product_capacity(db: AsyncSession, tenant_id: int) -> None:
    subscription = await require_active_subscription(db, tenant_id)
    current = await count_products_for_tenant(db, tenant_id)
    require_within_limit(subscription, "products", current)


async def enforce_store_capacity(db: AsyncSession, tenant_id: int) -> None:
    subscription = await require_active_subscription(db, tenant_id)
    current = await count_stores_for_tenant(db, tenant_id)
    require_within_limit(subscription, "stores", current)


async def enforce_staff_capacity(db: AsyncSession, tenant_id: int) -> None:
    subscription = await require_active_subscription(db, tenant_id)
    current = await count_staff_for_tenant(db, tenant_id)
    require_within_limit(subscription, "staff_seats", current)


async def enforce_orders_meter(
    db: AsyncSession, tenant_id: int, *, additional: int = 1
) -> None:
    """Monthly metered order limit (orders_per_month feature key)."""
    subscription = await require_active_subscription(db, tenant_id)
    await require_usage_within_limit(
        db, subscription, "orders_per_month", additional=additional
    )


async def enforce_boolean_feature(
    db: AsyncSession, tenant_id: int, feature_key: str
) -> None:
    subscription = await require_active_subscription(db, tenant_id)
    require_feature(subscription, feature_key)


def plan_limit_or_none(subscription: Subscription, feature_key: str) -> int | None:
    return feature_limit(subscription, feature_key)
