from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.rbac.models.rbac import Permission
from app.modules.rbac.schemas.rbac import CreateRoleRequest, PermissionResponse, TenantRoleResponse, UpdateRolePermissionsRequest
from app.modules.rbac.services.rbac import create_custom_role, get_role, list_roles, replace_role_permissions, role_permissions, require_permission
from app.modules.tenancy.models.tenant import Tenant
from app.modules.tenancy.services.tenant import get_tenant_by_public_id

router = APIRouter(prefix="/tenants/{tenant_public_id}/roles", tags=["roles"])


async def resolve_tenant(db: AsyncSession, tenant_public_id: str) -> Tenant:
    tenant = await get_tenant_by_public_id(db, tenant_public_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("", response_model=list[TenantRoleResponse])
async def roles(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[TenantRoleResponse]:
    tenant = await resolve_tenant(db, tenant_public_id)
    await require_permission(db, user, tenant.id, "roles.read")
    items = await list_roles(db, tenant.id)
    return [TenantRoleResponse(public_id=r.public_id, name=r.name, slug=r.slug, is_system=r.is_system, permissions=await role_permissions(db, r.id)) for r in items]


@router.get("/permissions", response_model=list[PermissionResponse])
async def permissions(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[PermissionResponse]:
    tenant = await resolve_tenant(db, tenant_public_id)
    await require_permission(db, user, tenant.id, "roles.read")
    rows = list((await db.execute(select(Permission).order_by(Permission.key))).scalars().all())
    return [PermissionResponse(key=p.key, name=p.name) for p in rows]


@router.post("", response_model=TenantRoleResponse, status_code=201)
async def create_role(tenant_public_id: str, payload: CreateRoleRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TenantRoleResponse:
    tenant = await resolve_tenant(db, tenant_public_id)
    await require_permission(db, user, tenant.id, "roles.manage")
    role = await create_custom_role(db, tenant.id, payload.name, payload.slug, payload.permissions)
    await db.commit()
    return TenantRoleResponse(public_id=role.public_id, name=role.name, slug=role.slug, is_system=role.is_system, permissions=await role_permissions(db, role.id))


@router.put("/{role_public_id}/permissions", response_model=TenantRoleResponse)
async def update_role_permissions(tenant_public_id: str, role_public_id: str, payload: UpdateRolePermissionsRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TenantRoleResponse:
    tenant = await resolve_tenant(db, tenant_public_id)
    await require_permission(db, user, tenant.id, "roles.manage")
    role = await get_role(db, tenant.id, role_public_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    role = await replace_role_permissions(db, role, payload.permissions)
    await db.commit()
    return TenantRoleResponse(public_id=role.public_id, name=role.name, slug=role.slug, is_system=role.is_system, permissions=await role_permissions(db, role.id))
