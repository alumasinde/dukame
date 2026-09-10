from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.onboarding.schemas.onboarding import (
    CompleteOnboardingRequest,
    OnboardingStatus,
)
from app.modules.onboarding.services.onboarding import complete_onboarding, get_onboarding_status

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatus)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatus:
    return await get_onboarding_status(db, user.id)


@router.post("/shop", response_model=OnboardingStatus, status_code=status.HTTP_201_CREATED)
async def complete_shop_setup(
    payload: CompleteOnboardingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatus:
    return await complete_onboarding(db, user, payload.shop_name, payload.shop_slug)
