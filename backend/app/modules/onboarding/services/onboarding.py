from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.onboarding.schemas.onboarding import OnboardingStatus
from app.modules.tenancy.models.tenant import Tenant, TenantUser
from app.modules.tenancy.services.tenant import create_tenant

TOTAL_STEPS = 1


async def get_onboarding_status(db: AsyncSession, user_id: int) -> OnboardingStatus:
    row = await db.execute(
        select(Tenant.public_id)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(TenantUser.user_id == user_id, TenantUser.status == "active")
        .order_by(Tenant.created_at)
        .limit(1)
    )
    tenant_public_id = row.scalar_one_or_none()
    completed = tenant_public_id is not None
    return OnboardingStatus(
        completed=completed,
        current_step=None if completed else "shop",
        total_steps=TOTAL_STEPS,
        tenant_public_id=tenant_public_id,
    )


async def complete_onboarding(
    db: AsyncSession, user: User, shop_name: str, shop_slug: str | None
) -> OnboardingStatus:
    existing = await get_onboarding_status(db, user.id)
    if existing.completed:
        return existing

    tenant, _ = await create_tenant(db, user, shop_name, shop_slug)
    return OnboardingStatus(
        completed=True,
        current_step=None,
        total_steps=TOTAL_STEPS,
        tenant_public_id=tenant.public_id,
    )
