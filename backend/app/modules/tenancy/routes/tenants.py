from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.tenancy.models.business_type import BusinessType
from app.modules.tenancy.schemas.tenant import CreateTenantRequest, TenantListResponse, TenantResponse
from app.modules.tenancy.services.tenant import create_tenant, get_user_tenants

router = APIRouter(prefix="/tenants", tags=["tenancy"])


@router.get("", response_model=TenantListResponse)
async def list_tenants(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TenantListResponse:
    rows = await get_user_tenants(db, user.id)
    return TenantListResponse(
        items=[
            TenantResponse(
                public_id=t.public_id,
                name=t.name,
                slug=t.slug,
                status=t.status,
                role=membership.role,
                business_type_public_id=t.business_type.public_id if t.business_type else None,
                business_type_name=t.business_type.name if t.business_type else None,
            )
            for t, membership in rows
        ]
    )


@router.post("", response_model=TenantResponse, status_code=201)
async def create_shop(payload: CreateTenantRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TenantResponse:
    business_type_id = None
    business_type = None
    if payload.business_type_public_id:
        business_type = await db.scalar(select(BusinessType).where(BusinessType.public_id == payload.business_type_public_id, BusinessType.is_active.is_(True)))
        if business_type is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="Select a valid business type")
        business_type_id = business_type.id
    tenant, _ = await create_tenant(db, user, payload.name, payload.slug, business_type_id)
    return TenantResponse(
        public_id=tenant.public_id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        role="owner",
        business_type_public_id=business_type.public_id if business_type else None,
        business_type_name=business_type.name if business_type else None,
    )
