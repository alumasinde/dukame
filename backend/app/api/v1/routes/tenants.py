from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tenant import CreateTenantRequest, TenantListResponse, TenantResponse
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import User
from app.services.auth import get_user_tenants
from app.services.tenant_phase2 import create_tenant

router = APIRouter(prefix="/tenants", tags=["tenancy"])


@router.get("", response_model=TenantListResponse)
async def list_tenants(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TenantListResponse:
    rows = await get_user_tenants(db, user.id)
    return TenantListResponse(items=[TenantResponse(public_id=t.public_id, name=t.name, slug=t.slug, status=t.status, role=membership.role) for t, membership in rows])


@router.post("", response_model=TenantResponse, status_code=201)
async def create_shop(payload: CreateTenantRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TenantResponse:
    tenant, _ = await create_tenant(db, user, payload.name, payload.slug)
    return TenantResponse(public_id=tenant.public_id, name=tenant.name, slug=tenant.slug, status=tenant.status, role="owner")
