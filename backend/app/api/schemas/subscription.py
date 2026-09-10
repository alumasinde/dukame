from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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
    is_active: bool
    features: list[PlanFeatureResponse]


class SubscriptionResponse(BaseModel):
    public_id: str
    status: str
    billing_interval: str
    starts_at: datetime
    current_period_end: datetime | None
    cancel_at_period_end: bool
    plan: PlanResponse
