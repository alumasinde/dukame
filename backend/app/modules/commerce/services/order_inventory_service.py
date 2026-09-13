# app/modules/commerce/services/order_inventory_service.py
from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.commerce.models.inventory_movement import InventoryMovement
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.stock_reservation import StockReservation
from app.modules.commerce.services.order_helpers import (
    _lock_product,
    _lock_variant,
)


class OrderInventoryService:
    """Handles inventory movements and stock reservations for orders."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def finalize_order_payment(self, order_id: int) -> None:
        """
        Called after a payment provider confirms payment.

        Converts pending reservations into inventory sales. The caller
        should commit this operation as part of its payment callback
        transaction.
        """
        order = await self.db.scalar(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
        )

        if order is None:
            return

        reservations = list(
            (
                await self.db.scalars(
                    select(StockReservation)
                    .options(
                        selectinload(StockReservation.product),
                        selectinload(StockReservation.variant),
                    )
                    .where(
                        StockReservation.order_id == order_id,
                        StockReservation.status == "pending",
                    )
                    .with_for_update()
                )
            ).all()
        )

        now = datetime.now(UTC)

        for reservation in reservations:
            inventory_owner = (
                reservation.variant or reservation.product
            )

            if inventory_owner.inventory_tracking:
                quantity_before = inventory_owner.inventory_quantity
                quantity_after = quantity_before - reservation.quantity

                if quantity_after < 0:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Insufficient inventory for "
                            f"{reservation.product.name}"
                        ),
                    )

                inventory_owner.inventory_quantity = quantity_after

                self.db.add(
                    InventoryMovement(
                        public_id=secrets.token_hex(16),
                        store_id=order.store_id,
                        product_id=reservation.product_id,
                        variant_id=reservation.variant_id,
                        movement_type="sale",
                        quantity=reservation.quantity,
                        quantity_before=quantity_before,
                        quantity_after=quantity_after,
                        reference_type="stock_reservation",
                        reference_id=reservation.id,
                    )
                )

            reservation.status = "finalized"
            reservation.finalized_at = now

    async def _release_order_reservations(
        self,
        order_id: int,
        reason: str = "payment_failed",
    ) -> None:
        """Release all pending stock reservations for an order."""
        reservations = list(
            (
                await self.db.scalars(
                    select(StockReservation)
                    .where(
                        StockReservation.order_id == order_id,
                        StockReservation.status == "pending",
                    )
                    .with_for_update()
                )
            ).all()
        )

        now = datetime.now(UTC)

        for reservation in reservations:
            reservation.status = "released"
            reservation.released_at = now
            reservation.release_reason = reason

    async def restore_cancelled_order_inventory(
        self,
        order: Order,
        store_id: int,
        actor_user_id: int,
    ) -> None:
        """
        Restore inventory for a cancelled order.

        A return movement is created only once per order item. Pending
        reservations are released separately and are not added to stock.
        """
        items = list(
            (
                await self.db.scalars(
                    select(OrderItem)
                    .where(OrderItem.order_id == order.id)
                    .order_by(OrderItem.id)
                )
            ).all()
        )

        for item in items:
            if item.variant_id is not None:
                owner = await _lock_variant(self.db, item.variant_id)
            else:
                owner = await _lock_product(self.db, item.product_id)

            if owner is None or not owner.inventory_tracking:
                continue

            existing_return = await self.db.scalar(
                select(InventoryMovement).where(
                    InventoryMovement.store_id == store_id,
                    InventoryMovement.reference_type == "order_item",
                    InventoryMovement.reference_id == item.id,
                    InventoryMovement.movement_type == "return",
                )
            )

            if existing_return is not None:
                continue

            quantity_before = owner.inventory_quantity
            quantity_after = quantity_before + item.quantity
            owner.inventory_quantity = quantity_after

            self.db.add(
                InventoryMovement(
                    public_id=secrets.token_hex(16),
                    store_id=store_id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    movement_type="return",
                    quantity=item.quantity,
                    quantity_before=quantity_before,
                    quantity_after=quantity_after,
                    reference_type="order_item",
                    reference_id=item.id,
                )
            )