import re
import uuid
from datetime import timedelta
from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import utc_now
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.commerce.models.payment_method import PaymentMethod
from app.modules.rbac.models.rbac import Permission, TenantRole, TenantRolePermission
from app.modules.subscriptions.models.subscription import Plan, Subscription, SubscriptionEvent
from app.modules.tenancy.models.tenant import Tenant, TenantUser

DEFAULT_ROLES = (("Owner", "owner"), ("Administrator", "admin"), ("Manager", "manager"), ("Staff", "staff"))
DEFAULT_ROLE_PERMISSIONS = {
    "owner": None,
    "admin": {"tenant.read", "tenant.manage", "members.read", "members.manage", "roles.read", "roles.manage", "subscription.read", "account.read", "account.manage", "payments.read", "payments.manage"},
    "manager": {"tenant.read", "members.read", "roles.read", "subscription.read", "account.read", "payments.read", "payments.manage"},
    "staff": {"tenant.read", "account.read", "payments.read"},
}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return value.strip("-")[:100]


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


async def create_tenant(db: AsyncSession, user: User, name: str, slug: str | None, business_type_id: int | None = None) -> tuple[Tenant, Subscription]:
    tenant_slug = slugify(slug or name)
    if len(tenant_slug) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid business name or link is required")
    if await db.scalar(select(Tenant).where(Tenant.slug == tenant_slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This business link is already in use")
    plan = cast(Plan | None, await db.scalar(select(Plan).where(Plan.slug == settings.default_plan_slug, Plan.is_active.is_(True))))
    if plan is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Default subscription plan is unavailable")
    business_name = name.strip()
    tenant = Tenant(public_id=uuid.uuid4().hex, name=business_name, slug=tenant_slug, business_type_id=business_type_id)
    db.add(tenant)
    await db.flush()
    store = Store(public_id=uuid.uuid4().hex, tenant_id=tenant.id, name=business_name, slug=tenant_slug, status="active", currency="KES")
    db.add(store)
    await db.flush()
    db.add(PaymentMethod(public_id=uuid.uuid4().hex, store_id=store.id, code="cash", name="Cash", is_enabled=True, sort_order=10, instructions="Pay the store in cash when your order is delivered or collected."))
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Business details are already in use") from exc
    await db.refresh(tenant)
    await db.refresh(subscription)
    return tenant, subscription


async def get_tenant_by_public_id(db: AsyncSession, public_id: str) -> Tenant | None:
    return cast(Tenant | None, await db.scalar(select(Tenant).where(Tenant.public_id == public_id)))


async def get_user_tenants(db: AsyncSession, user_id: int) -> list[tuple[Tenant, TenantUser]]:
    result = await db.execute(
        select(Tenant, TenantUser)
        .options(selectinload(Tenant.business_type))
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(TenantUser.user_id == user_id, TenantUser.status == "active")
        .order_by(Tenant.name)
    )
    return [(row[0], row[1]) for row in result.all()]
