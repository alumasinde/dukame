from pydantic import BaseModel, Field


class InventoryAdjustmentRequest(BaseModel):
    variant_public_id: str | None = Field(default=None, min_length=1, max_length=32)
    delta: int = Field(ne=0)
    movement_type: str = Field(min_length=3, max_length=32)
    reason: str | None = Field(default=None, max_length=500)


class InventoryMovementResponse(BaseModel):
    public_id: str
    product_public_id: str
    variant_public_id: str | None
    movement_type: str
    quantity: int
    quantity_before: int
    quantity_after: int
    reason: str | None
    actor_user_id: int | None
    created_at: str
