import re
import uuid
from datetime import timedelta
from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import utc_now
from app.models.identity import Tenant, TenantUser, User
from app.models.rbac import Permission, TenantRole, TenantRolePermission
from app.models.subscription import Plan, Subscription, SubscriptionEvent

DEFAULT_ROLES = (("Owner", "owner"), ("Administrator", "admin"), ("Manager", "manager"), ("Staff", "staff"))
DEFAULT_ROLE_PERMISSIONS = {
    "owner": None,
    "admin": {"tenant.read", "tenant.manage", "members.read", "members.manage", "roles.read", "roles.manage", "subscription.read", "account.read", "account.manage"},
    "manager": {"tenant.read", "members.read", "roles.read", "subscription.read", "account.read"},
    "staff": {"tenant.read", "account.read"},
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")[:100]


async def ensure_default_roles(db: AsyncSession, tenant_id: int) -> TenantRole:
    roles = list((await db.execute(select(TenantRole).where(TenantRole.tenant_id == tenant_id))).scalars().all())
    by_slug = {role.slug: role for role in roles}
    for name, slug in DEFAULT_ROLES:
        if slug not in by_slug:
            role = TenantRole(public_id=uuid.uuid4().hex, tenant_id=tenant_id, name=name, slug=slug, is_system=True)
            db.add(role)
            await db.flush()
            by_slug[slug] = role
    permissions = list((await db.execute(select(Permission))).scalars().all())
    permission_by_key = {permission.key: permission for permission in permissions}
    for slug, keys in DEFAULT_ROLE_PERMISSIONS.items():
        role = by_slug[slug]
        selected = permissions if keys is None else [permission_by_key[key] for key in keys if key in permission_by_key]
        existing = set((await db.execute(select(TenantRolePermission.permission_id).where(TenantRolePermission.role_id == role.id))).scalars().all())
        db.add_all(TenantRolePermission(role_id=role.id, permission_id=p.id) for p in selected if p.id not in existing)
    await db.flush()
    return by_slug["owner"]


async def create_tenant(db: AsyncSession, user: User, name: str, slug: str | None) -> tuple[Tenant, Subscription]:
    tenant_slug = slugify(slug or name)
    if len(tenant_slug) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid shop name or slug is required")
    if await db.scalar(select(Tenant).where(Tenant.slug == tenant_slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shop slug is already in use")
    plan = cast(Plan | None, await db.scalar(select(Plan).where(Plan.slug == settings.default_plan_slug, Plan.is_active.is_(True))))
    if plan is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Default subscription plan is unavailable")
    tenant = Tenant(public_id=uuid.uuid4().hex, name=name.strip(), slug=tenant_slug)
    db.add(tenant)
    await db.flush()
    owner_role = await ensure_default_roles(db, tenant.id)
    db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role="owner", role_id=owner_role.id, status="active"))
    start = utc_now()
    period_days = 30 + plan.trial_days
    subscription = Subscription(public_id=uuid.uuid4().hex, tenant_id=tenant.id, plan_id=plan.id, status="trial" if plan.trial_days else "active", billing_interval="monthly", starts_at=start, current_period_end=start + timedelta(days=period_days))
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


async def get_tenant_by_public_id(db: AsyncSession, public_id: str) -> Tenant | None:
    return cast(Tenant | None, await db.scalar(select(Tenant).where(Tenant.public_id == public_id)))
