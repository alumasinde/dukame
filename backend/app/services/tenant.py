import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.identity import Tenant, TenantUser, User
from app.models.subscription import Plan, Subscription, SubscriptionEvent


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return value[:100]


async def create_tenant(db: AsyncSession, user: User, name: str, slug: str | None) -> tuple[Tenant, Subscription]:
    tenant_slug = slug or slugify(name)
    if len(tenant_slug) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid shop name or slug is required")
    if await db.scalar(select(Tenant).where(Tenant.slug == tenant_slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shop slug is already in use")
    plan = await db.scalar(select(Plan).where(Plan.slug == settings.default_plan_slug, Plan.is_active.is_(True)))
    if plan is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Default subscription plan is unavailable")
    tenant = Tenant(public_id=uuid.uuid4().hex, name=name.strip(), slug=tenant_slug)
    db.add(tenant)
    await db.flush()
    db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role="owner", status="active"))
    subscription = Subscription(public_id=uuid.uuid4().hex, tenant_id=tenant.id, plan_id=plan.id, status="active", billing_interval="monthly", starts_at=datetime.now(timezone.utc))
    db.add(subscription)
    await db.flush()
    db.add(SubscriptionEvent(public_id=uuid.uuid4().hex, subscription_id=subscription.id, event_type="subscription.created", payload={"source": "tenant.created", "plan": plan.slug}))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shop details are already in use") from exc
    await db.refresh(tenant)
    await db.refresh(subscription)
    return tenant, subscription
