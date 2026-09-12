from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.commerce.inventory_schemas import InventoryAdjustmentRequest, InventoryMovementResponse
from app.modules.commerce.inventory_service import InventoryService

router = APIRouter(prefix="/tenants/{tenant_public_id}/products/{product_public_id}/inventory", tags=["inventory"])


@router.post("/adjust", response_model=InventoryMovementResponse, status_code=status.HTTP_201_CREATED)
async def adjust_inventory(
    tenant_public_id: str,
    product_public_id: str,
    payload: InventoryAdjustmentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InventoryMovementResponse:
    movement = await InventoryService(db).adjust(
        user,
        tenant_public_id,
        product_public_id,
        payload.variant_public_id,
        payload.delta,
        payload.movement_type,
        payload.reason,
    )
    return InventoryMovementResponse(
        public_id=movement.public_id,
        product_public_id=product_public_id,
        variant_public_id=payload.variant_public_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        quantity_before=movement.quantity_before,
        quantity_after=movement.quantity_after,
        reason=movement.reason,
        actor_user_id=movement.actor_user_id,
        created_at=movement.created_at.isoformat(),
    )
