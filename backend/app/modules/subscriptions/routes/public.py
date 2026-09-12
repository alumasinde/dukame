from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.subscriptions.models.subscription import Plan
from app.modules.subscriptions.schemas.subscription import (
    PublicPlanResponse,
    PublicPricingResponse,
)
from app.modules.subscriptions.services.subscription import (
    get_public_plan_by_slug,
    list_public_plans,
)

router = APIRouter(prefix="/public", tags=["public-pricing"])


def public_plan_response(plan: Plan) -> PublicPlanResponse:
    return PublicPlanResponse.model_validate(plan, from_attributes=True)


@router.get("/plans", response_model=PublicPricingResponse)
async def public_pricing(db: AsyncSession = Depends(get_db)) -> PublicPricingResponse:
    """Public pricing catalog for the marketing / landing page.

    No authentication required. Only active + public plans are returned.
    Plan names, prices and features come from the database — not application constants.
    """
    plans = await list_public_plans(db)
    return PublicPricingResponse(
        currency_default=settings.default_billing_currency,
        intervals=list(settings.billing_intervals),
        plans=[public_plan_response(plan) for plan in plans],
    )


@router.get("/plans/{slug}", response_model=PublicPlanResponse)
async def public_plan_detail(
    slug: str, db: AsyncSession = Depends(get_db)
) -> PublicPlanResponse:
    plan = await get_public_plan_by_slug(db, slug)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return public_plan_response(plan)
