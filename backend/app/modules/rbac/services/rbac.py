import re
import uuid
from typing import cast

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.rbac.models.rbac import Permission, TenantRole, TenantRolePermission
from app.modules.tenancy.models.tenant import TenantUser


async def get_membership(db: AsyncSession, user_id: int, tenant_id: int) -> TenantUser | None:
    return cast(TenantUser | None, await db.scalar(select(TenantUser).where(TenantUser.user_id == user_id, TenantUser.tenant_id == tenant_id, TenantUser.status == "active")))


async def require_permission(db: AsyncSession, user: User, tenant_id: int, permission_key: str) -> TenantUser:
    membership = await get_membership(db, user.id, tenant_id)
    if membership is None or membership.role_id is None:
        raise HTTPException(status_code=403, detail="Tenant access denied")
    allowed = await db.scalar(select(Permission.id).join(TenantRolePermission, TenantRolePermission.permission_id == Permission.id).where(TenantRolePermission.role_id == membership.role_id, Permission.key == permission_key))
    if allowed is None:
        raise HTTPException(status_code=403, detail="Permission denied")
    return membership


async def list_roles(db: AsyncSession, tenant_id: int) -> list[TenantRole]:
    return list((await db.execute(select(TenantRole).where(TenantRole.tenant_id == tenant_id).order_by(TenantRole.name))).scalars().all())


async def get_role(db: AsyncSession, tenant_id: int, role_public_id: str) -> TenantRole | None:
    return cast(TenantRole | None, await db.scalar(select(TenantRole).where(TenantRole.tenant_id == tenant_id, TenantRole.public_id == role_public_id)))


async def role_permissions(db: AsyncSession, role_id: int) -> list[str]:
    result = await db.execute(select(Permission.key).join(TenantRolePermission, TenantRolePermission.permission_id == Permission.id).where(TenantRolePermission.role_id == role_id).order_by(Permission.key))
    return list(result.scalars().all())


async def create_custom_role(db: AsyncSession, tenant_id: int, name: str, slug: str | None, permission_keys: list[str]) -> TenantRole:
    role_slug = re.sub(r"[^a-z0-9]+", "-", (slug or name).strip().lower()).strip("-")[:100]
    if len(role_slug) < 2:
        raise HTTPException(status_code=422, detail="Invalid role slug")
    if await db.scalar(select(TenantRole).where(TenantRole.tenant_id == tenant_id, TenantRole.slug == role_slug)):
        raise HTTPException(status_code=409, detail="Role slug is already in use")
    keys = set(permission_keys)
    permissions = list((await db.execute(select(Permission).where(Permission.key.in_(keys)))).scalars().all()) if keys else []
    if len(permissions) != len(keys):
        raise HTTPException(status_code=422, detail="One or more permissions are invalid")
    role = TenantRole(public_id=uuid.uuid4().hex, tenant_id=tenant_id, name=name.strip(), slug=role_slug, is_system=False)
    db.add(role)
    await db.flush()
    db.add_all([TenantRolePermission(role_id=role.id, permission_id=p.id) for p in permissions])
    await db.flush()
    return role


async def replace_role_permissions(db: AsyncSession, role: TenantRole, permission_keys: list[str]) -> TenantRole:
    if role.is_system and role.slug == "owner":
        raise HTTPException(status_code=400, detail="Owner permissions cannot be reduced")
    keys = set(permission_keys)
    permissions = list((await db.execute(select(Permission).where(Permission.key.in_(keys)))).scalars().all()) if keys else []
    if len(permissions) != len(keys):
        raise HTTPException(status_code=422, detail="One or more permissions are invalid")
    await db.execute(delete(TenantRolePermission).where(TenantRolePermission.role_id == role.id))
    db.add_all([TenantRolePermission(role_id=role.id, permission_id=p.id) for p in permissions])
    await db.flush()
    return role
