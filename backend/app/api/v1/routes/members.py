from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.rbac import MemberResponse, UpdateMemberRoleRequest
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import TenantUser, User
from app.models.rbac import TenantRole
from app.services.rbac import require_permission
from app.services.tenant import get_tenant_by_public_id

router = APIRouter(prefix="/tenants/{tenant_public_id}/members", tags=["members"])


@router.get("", response_model=list[MemberResponse])
async def members(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[MemberResponse]:
    tenant = await get_tenant_by_public_id(db, tenant_public_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await require_permission(db, user, tenant.id, "members.read")
    result = await db.execute(select(User, TenantUser, TenantRole).join(TenantUser, TenantUser.user_id == User.id).outerjoin(TenantRole, TenantRole.id == TenantUser.role_id).where(TenantUser.tenant_id == tenant.id).order_by(User.first_name, User.last_name))
    return [MemberResponse(user_public_id=u.public_id, email=u.email, first_name=u.first_name, last_name=u.last_name, role=r.name if r else m.role, status=m.status) for u, m, r in result.all()]


@router.put("/{member_public_id}/role", response_model=MemberResponse)
async def update_member_role(tenant_public_id: str, member_public_id: str, payload: UpdateMemberRoleRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> MemberResponse:
    tenant = await get_tenant_by_public_id(db, tenant_public_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await require_permission(db, user, tenant.id, "members.manage")
    role = await db.scalar(select(TenantRole).where(TenantRole.tenant_id == tenant.id, TenantRole.public_id == payload.role_public_id))
    member = await db.scalar(select(TenantUser).join(User, User.id == TenantUser.user_id).where(TenantUser.tenant_id == tenant.id, User.public_id == member_public_id))
    if role is None or member is None or member.status != "active":
        raise HTTPException(status_code=404, detail="Member or role not found")
    if role.slug == "owner" and member.user_id != user.id:
        current_role = await db.scalar(select(TenantRole).where(TenantRole.id == member.role_id, TenantRole.tenant_id == tenant.id))
        if current_role is None or current_role.slug != "owner":
            raise HTTPException(status_code=403, detail="Only an existing owner can assign the owner role")
    if member.user_id == user.id and role.slug != "owner":
        raise HTTPException(status_code=409, detail="Owners cannot remove their own owner role")
    member.role_id = role.id
    member.role = role.slug
    await db.commit()
    result = await db.execute(select(User, TenantUser, TenantRole).join(TenantUser, TenantUser.user_id == User.id).outerjoin(TenantRole, TenantRole.id == TenantUser.role_id).where(TenantUser.tenant_id == tenant.id, User.id == member.user_id))
    u, m, r = result.one()
    return MemberResponse(user_public_id=u.public_id, email=u.email, first_name=u.first_name, last_name=u.last_name, role=r.name if r else m.role, status=m.status)
