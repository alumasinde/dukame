from datetime import datetime

from pydantic import BaseModel, Field


class DeliveryAssignRequest(BaseModel):
    assigned_user_id: int = Field(gt=0)


class DeliveryConfirmRequest(BaseModel):
    otp: str = Field(min_length=4, max_length=12)
    note: str | None = Field(default=None, max_length=1000)


class DeliveryResponse(BaseModel):
    public_id: str
    order_public_id: str
    order_number: str
    status: str
    assigned_user_id: int | None
    delivered_at: datetime | None
    delivered_by_user_id: int | None
    delivery_note: str | None
    otp_expires_at: datetime | None
    otp_verified_at: datetime | None
    otp_attempts: int
    created_at: datetime
    updated_at: datetime


class DeliveryOtpResponse(BaseModel):
    delivery_public_id: str
    expires_at: datetime
    otp: str
