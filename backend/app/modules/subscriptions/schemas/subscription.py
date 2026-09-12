from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_key: str
    value: Any


class PlanResponse(BaseModel):
    """Full plan payload for authenticated merchant billing UI."""

    model_config = ConfigDict(from_attributes=True)

    public_id: str
    slug: str
    name: str
    description: str | None
    monthly_price_minor: int
    quarterly_price_minor: int
    yearly_price_minor: int
    currency: str
    trial_days: int
    is_active: bool
    is_public: bool = True
    sort_order: int = 100
    badge: str | None = None
    highlight: bool = False
    features: list[PlanFeatureResponse] = Field(default_factory=list)


class PublicPlanResponse(BaseModel):
    """Public marketing/pricing payload for the landing page (no internal flags)."""

    model_config = ConfigDict(from_attributes=True)

    public_id: str
    slug: str
    name: str
    description: str | None
    monthly_price_minor: int
    quarterly_price_minor: int
    yearly_price_minor: int
    currency: str
    trial_days: int
    badge: str | None = None
    highlight: bool = False
    sort_order: int = 100
    features: list[PlanFeatureResponse] = Field(default_factory=list)


class PublicPricingResponse(BaseModel):
    currency_default: str
    intervals: list[str]
    plans: list[PublicPlanResponse]


class SubscriptionChangeRequest(BaseModel):
    plan_public_id: str = Field(min_length=8, max_length=64)
    billing_interval: str = Field(
        default="monthly", pattern="^(monthly|quarterly|yearly)$"
    )


class SubscriptionCancelRequest(BaseModel):
    immediately: bool = False


class SubscriptionResponse(BaseModel):
    public_id: str
    status: str
    billing_interval: str
    starts_at: datetime
    current_period_end: datetime | None
    cancel_at_period_end: bool
    entitled: bool = True
    plan: PlanResponse


class SubscriptionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    event_type: str
    payload: dict[str, Any] | None = None
    created_at: datetime
