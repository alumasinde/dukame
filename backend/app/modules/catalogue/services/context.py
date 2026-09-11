from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.repositories.store import StoreRepository
from app.modules.rbac.services.rbac import require_permission
from app.modules.tenancy.services.tenant import get_tenant_by_public_id


async def resolve_store(db: AsyncSession, user: User, tenant_public_id: str, permission: str) -> Store:
    tenant = await get_tenant_by_public_id(db, tenant_public_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await require_permission(db, user, tenant.id, permission)
    store = await StoreRepository(db).get_by_tenant_id(tenant.id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return store
