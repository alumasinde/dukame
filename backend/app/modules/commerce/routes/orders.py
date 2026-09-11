from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models.identity import User
from app.modules.auth.security import get_current_user
from app.modules.commerce.routes.storefront import order_response
from app.modules.commerce.schemas import OrderResponse, OrderStatusResponse, OrderStatusUpdate
from app.modules.commerce.service import CommerceService

router = APIRouter(prefix="/tenants/{tenant_public_id}/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
async def list_orders(tenant_public_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), status_public_id: str | None = Query(default=None, max_length=32), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[OrderResponse]:
    orders = await CommerceService(db).list_orders(user, tenant_public_id, offset, limit, status_public_id)
    return [order_response(order) for order in orders]


@router.get("/statuses", response_model=list[OrderStatusResponse])
async def list_order_statuses(tenant_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[OrderStatusResponse]:
    statuses = await CommerceService(db).list_statuses(user, tenant_public_id)
    return [OrderStatusResponse(public_id=item.public_id, code=item.code, name=item.name, description=item.description, sort_order=item.sort_order, is_terminal=item.is_terminal) for item in statuses]


@router.get("/{order_public_id}/next-statuses", response_model=list[OrderStatusResponse])
async def list_next_order_statuses(tenant_public_id: str, order_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[OrderStatusResponse]:
    statuses = await CommerceService(db).list_next_statuses(user, tenant_public_id, order_public_id)
    return [OrderStatusResponse(public_id=item.public_id, code=item.code, name=item.name, description=item.description, sort_order=item.sort_order, is_terminal=item.is_terminal) for item in statuses]


@router.get("/{order_public_id}", response_model=OrderResponse)
async def get_order(tenant_public_id: str, order_public_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OrderResponse:
    order = await CommerceService(db).get_order(user, tenant_public_id, order_public_id)
    return order_response(order)


@router.patch("/{order_public_id}/status", response_model=OrderResponse)
async def update_order_status(tenant_public_id: str, order_public_id: str, payload: OrderStatusUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> OrderResponse:
    order = await CommerceService(db).update_order_status(user, tenant_public_id, order_public_id, payload)
    return order_response(order)
