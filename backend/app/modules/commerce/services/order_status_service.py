# app/modules/commerce/services/order_status_service.py
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models.identity import User
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.idempotency_key import IdempotencyKey
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.notifications import queue_order_sms
from app.modules.commerce.schemas import OrderStatusUpdate
from app.modules.commerce.services.idempotency import IdempotencyEngine
from app.modules.commerce.services.order_helpers import _load_order, _load_order_by_public_id
from app.modules.commerce.services.order_inventory_service import OrderInventoryService
from app.modules.rbac.services.rbac import require_permission


class OrderStatusService:
    """Handles order status updates and cancellation logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.idempotency = IdempotencyEngine(db)
        self.inventory_service = OrderInventoryService(db)

    async def update_order_status(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
        payload: OrderStatusUpdate,
        idempotency_key: str | None = None,
    ) -> Order:
        """Update an order's status with proper permission and transition checks."""
        store = await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        key = self.idempotency.validate_key(idempotency_key)
        request_hash = self.idempotency.calculate_hash(
            payload.model_dump(mode="json")
        )

        order = await _load_order_by_public_id(
            self.db,
            store.id,
            public_id,
            lock=True,
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if key:
            existing = await self.idempotency.claim_key(
                store.id,
                "commerce.order_status",
                order.public_id,
                key,
                request_hash,
            )
            if existing is not None:
                previous_order = await _load_order_by_public_id(
                    self.db,
                    store.id,
                    existing.resource_public_id,
                )
                if previous_order is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Order not found",
                    )
                return previous_order

        if order.status.is_terminal:
            raise HTTPException(
                status_code=409,
                detail="An order in a final status cannot be changed",
            )

        if not order.status.is_active:
            raise HTTPException(
                status_code=409,
                detail="The current order status is inactive",
            )

        status = await self.db.scalar(
            select(OrderStatus).where(
                OrderStatus.public_id == payload.status_public_id,
                OrderStatus.is_active.is_(True),
            )
        )

        if status is None:
            raise HTTPException(
                status_code=422,
                detail="Order status not found",
            )

        if status.id == order.status_id:
            raise HTTPException(
                status_code=409,
                detail="Order is already in this status",
            )

        transition = await self.db.scalar(
            select(OrderStatusTransition)
            .options(
                selectinload(OrderStatusTransition.permission)
            )
            .where(
                OrderStatusTransition.from_status_id == order.status_id,
                OrderStatusTransition.to_status_id == status.id,
            )
        )

        if transition is None or transition.permission is None:
            raise HTTPException(
                status_code=409,
                detail="The requested order transition is not configured",
            )

        await require_permission(
            self.db,
            user,
            store.tenant_id,
            transition.permission.key,
        )

        if status.code == "cancelled":
            await self.inventory_service._release_order_reservations(
                order.id,
                "order_cancelled",
            )
            await self.inventory_service.restore_cancelled_order_inventory(
                order,
                store.id,
                user.id,
            )

        order.status_id = status.id

        self.db.add(
            OrderStatusHistory(
                order_id=order.id,
                status_id=status.id,
                actor_user_id=user.id,
                source="merchant",
            )
        )

        await queue_order_sms(
            self.db,
            order,
            status,
            store.name,
            store.slug,
        )

        if key:
            self.db.add(
                IdempotencyKey(
                    store_id=store.id,
                    operation="commerce.order_status",
                    scope_key=order.public_id,
                    key=key,
                    request_hash=request_hash,
                    resource_public_id=order.public_id,
                    response_hash="",
                )
            )

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()

            if key:
                existing = await self.idempotency.claim_key(
                    store.id,
                    "commerce.order_status",
                    order.public_id,
                    key,
                    request_hash,
                )
                if existing is not None:
                    previous_order = await _load_order_by_public_id(
                        self.db,
                        store.id,
                        existing.resource_public_id,
                    )
                    if previous_order is not None:
                        return previous_order

            raise

        return await _load_order(self.db, order.id)