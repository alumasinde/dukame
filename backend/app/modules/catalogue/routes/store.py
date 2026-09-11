from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.catalogue.schemas.store import StoreCreate, StoreResponse, StoreUpdate
from app.modules.catalogue.services.store import StoreService

router = APIRouter(prefix="/tenants/{tenant_public_id}/store", tags=["catalogue"])


@router.get("", response_model=StoreResponse)
async def get_store(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> StoreResponse:
    return await StoreService(db).get(user, tenant_public_id)


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(tenant_public_id: str, payload: StoreCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> StoreResponse:
    return await StoreService(db).create(user, tenant_public_id, payload)


@router.put("", response_model=StoreResponse)
async def update_store(tenant_public_id: str, payload: StoreUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> StoreResponse:
    return await StoreService(db).update(user, tenant_public_id, payload)
