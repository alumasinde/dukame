from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity import Tenant, TenantUser, User
from app.models.subscription import Plan, Subscription


async def list_active_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).where(Plan.is_active.is_(True)).options(selectinload(Plan.features)).order_by(Plan.monthly_price_minor, Plan.id))
    return list(result.scalars().unique().all())


async def get_tenant_subscription(db: AsyncSession, user: User, tenant_public_id: str) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .join(Tenant, Tenant.id == Subscription.tenant_id)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(Tenant.public_id == tenant_public_id, TenantUser.user_id == user.id, TenantUser.status == "active")
        .options(selectinload(Subscription.plan).selectinload(Plan.features))
    )
    return result.scalar_one_or_none()
