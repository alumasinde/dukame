from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.tenancy.schemas.business_type import BusinessTypeListResponse
from app.modules.tenancy.services.business_type import list_business_types

router = APIRouter(prefix="/business-types", tags=["business types"])


@router.get("", response_model=BusinessTypeListResponse)
async def get_business_types(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessTypeListResponse:
    return BusinessTypeListResponse(items=await list_business_types(db))
