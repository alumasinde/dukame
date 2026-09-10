from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import TenantUser, User
from app.models.subscription import PlanFeature, Subscription


async def get_feature(db: AsyncSession, user: User, tenant_id: int, feature_key: str) -> Any:
    subscription = await db.scalar(select(Subscription).join(TenantUser, TenantUser.tenant_id == Subscription.tenant_id).where(Subscription.tenant_id == tenant_id, TenantUser.user_id == user.id, TenantUser.status == "active"))
    if subscription is None or subscription.status in {"suspended", "cancelled"}:
        return None
    feature = await db.scalar(select(PlanFeature).where(PlanFeature.plan_id == subscription.plan_id, PlanFeature.feature_key == feature_key))
    return feature.value if feature else None


async def require_feature(db: AsyncSession, user: User, tenant_id: int, feature_key: str) -> Any:
    value = await get_feature(db, user, tenant_id, feature_key)
    if value is None or value is False:
        raise HTTPException(status_code=403, detail="This feature is not available on the current plan")
    return value
