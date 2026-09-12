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
    is_public: bool = True
    sort_order: int = 100
    badge: str | None = None
    highlight: bool = False
    features: list[PlanFeatureResponse] = Field(default_factory=list)


class PublicPlanResponse(BaseModel):
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


class SubscriptionUpgradeRequest(BaseModel):
    plan_public_id: str = Field(min_length=8, max_length=64)
    billing_interval: str = Field(
        default="monthly", pattern="^(monthly|quarterly|yearly)$"
    )
    phone: str | None = Field(default=None, min_length=9, max_length=20)


class SubscriptionPayInvoiceRequest(BaseModel):
    phone: str = Field(min_length=9, max_length=20)


class SubscriptionMarkPaidRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


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


class SubscriptionPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    status: str
    provider: str
    amount_minor: int
    currency: str
    phone: str | None = None
    provider_checkout_request_id: str | None = None
    provider_reference: str | None = None
    failure_reason: str | None = None
    paid_at: datetime | None = None
    created_at: datetime


class SubscriptionInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    status: str
    purpose: str
    billing_interval: str
    currency: str
    amount_minor: int
    period_start: datetime | None = None
    period_end: datetime | None = None
    due_at: datetime | None = None
    paid_at: datetime | None = None
    plan_public_id: str | None = None
    payments: list[SubscriptionPaymentResponse] = Field(default_factory=list)
    created_at: datetime


class UpgradeResponse(BaseModel):
    subscription: SubscriptionResponse
    invoice: SubscriptionInvoiceResponse
    payment: SubscriptionPaymentResponse | None = None


class UsageItemResponse(BaseModel):
    feature_key: str
    quantity: int
    limit: int | None = None
    period_key: str


class UsageSnapshotResponse(BaseModel):
    period_key: str
    items: list[UsageItemResponse]
