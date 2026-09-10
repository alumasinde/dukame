from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    feature_key: str
    value: Any


class PlanResponse(BaseModel):
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
    features: list[PlanFeatureResponse]


class SubscriptionChangeRequest(BaseModel):
    plan_public_id: str = Field(min_length=8, max_length=64)
    billing_interval: str = Field(default="monthly", pattern="^(monthly|quarterly|yearly)$")


class SubscriptionCancelRequest(BaseModel):
    immediately: bool = False


class SubscriptionResponse(BaseModel):
    public_id: str
    status: str
    billing_interval: str
    starts_at: datetime
    current_period_end: datetime | None
    cancel_at_period_end: bool
    plan: PlanResponse
