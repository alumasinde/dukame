from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.commerce.delivery_schemas import DeliveryAssignRequest, DeliveryConfirmRequest, DeliveryOtpResponse, DeliveryResponse
from app.modules.commerce.delivery_service import DeliveryService

router = APIRouter(prefix="/tenants/{tenant_public_id}/orders/{order_public_id}/delivery", tags=["delivery"])


def response(delivery, order) -> DeliveryResponse:
    return DeliveryResponse(
        public_id=delivery.public_id,
        order_public_id=order.public_id,
        order_number=order.order_number,
        status=delivery.status,
        assigned_user_id=delivery.assigned_user_id,
        delivered_at=delivery.delivered_at,
        delivered_by_user_id=delivery.delivered_by_user_id,
        delivery_note=delivery.delivery_note,
        otp_expires_at=delivery.otp_expires_at,
        otp_verified_at=delivery.otp_verified_at,
        otp_attempts=delivery.otp_attempts,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )


@router.get("", response_model=DeliveryResponse)
async def get_delivery(tenant_public_id: str, order_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DeliveryResponse:
    delivery = await DeliveryService(db).get_or_create(user, tenant_public_id, order_public_id)
    return response(delivery, delivery.order)


@router.post("/assign", response_model=DeliveryResponse)
async def assign_delivery(tenant_public_id: str, order_public_id: str, payload: DeliveryAssignRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DeliveryResponse:
    delivery = await DeliveryService(db).assign(user, tenant_public_id, order_public_id, payload.assigned_user_id)
    await db.refresh(delivery, ["order"])
    return response(delivery, delivery.order)


@router.post("/otp", response_model=DeliveryOtpResponse, status_code=status.HTTP_201_CREATED)
async def issue_delivery_otp(tenant_public_id: str, order_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DeliveryOtpResponse:
    delivery, otp = await DeliveryService(db).issue_otp(user, tenant_public_id, order_public_id)
    return DeliveryOtpResponse(delivery_public_id=delivery.public_id, expires_at=delivery.otp_expires_at, otp=otp)


@router.post("/confirm", response_model=DeliveryResponse)
async def confirm_delivery(tenant_public_id: str, order_public_id: str, payload: DeliveryConfirmRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DeliveryResponse:
    delivery = await DeliveryService(db).confirm(user, tenant_public_id, order_public_id, payload.otp, payload.note)
    await db.refresh(delivery, ["order"])
    return response(delivery, delivery.order)
