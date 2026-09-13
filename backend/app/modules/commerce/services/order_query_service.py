# app/modules/commerce/services/order_query_service.py
from __future__ import annotations

import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models.identity import User
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.services.order_helpers import (
    _load_order,
    _load_order_by_public_id,
)
from app.modules.commerce.tracking import tracking_token, tracking_token_hash


class OrderQueryService:
    """Handles order queries and retrieval operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_orders(
        self,
        user: User,
        tenant_public_id: str,
        offset: int,
        limit: int,
        status_public_id: str | None,
    ) -> list[Order]:
        """List orders for a tenant with optional status filter."""
        store = await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        stmt = (
            select(Order)
            .options(
                selectinload(Order.status),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
                selectinload(Order.customer),
                selectinload(Order.payment),
                selectinload(Order.status_history).selectinload(
                    OrderStatusHistory.status
                ),
            )
            .where(Order.store_id == store.id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if status_public_id:
            stmt = stmt.join(Order.status).where(
                OrderStatus.public_id == status_public_id
            )

        return list((await self.db.scalars(stmt)).unique().all())

    async def get_order(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
    ) -> Order:
        """Get a single order by public ID."""
        store = await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        order = await _load_order_by_public_id(
            self.db,
            store.id,
            public_id,
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        return order

    async def list_statuses(
        self,
        user: User,
        tenant_public_id: str,
    ) -> list[OrderStatus]:
        """List all active order statuses."""
        await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        return list(
            (
                await self.db.scalars(
                    select(OrderStatus)
                    .where(OrderStatus.is_active.is_(True))
                    .order_by(
                        OrderStatus.sort_order,
                        OrderStatus.id,
                    )
                )
            ).all()
        )

    async def list_next_statuses(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
    ) -> list[OrderStatus]:
        """List possible next statuses for an order."""
        store = await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        order = await _load_order_by_public_id(
            self.db,
            store.id,
            public_id,
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.status.is_terminal:
            return []

        stmt = (
            select(OrderStatus)
            .join(
                OrderStatusTransition,
                OrderStatusTransition.to_status_id == OrderStatus.id,
            )
            .where(
                OrderStatusTransition.from_status_id == order.status_id,
                OrderStatus.is_active.is_(True),
            )
            .order_by(OrderStatus.sort_order, OrderStatus.id)
        )

        return list((await self.db.scalars(stmt)).all())

    async def get_public_order(
        self,
        store: Store,
        token: str,
    ) -> Order:
        """Get a public order using tracking token."""
        parts = token.split(".", 1)

        if len(parts) != 2 or not parts[0]:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        public_id = parts[0]
        expected_token = tracking_token(public_id)

        if not secrets.compare_digest(expected_token, token):
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        order = await self.db.scalar(
            select(Order)
            .options(
                selectinload(Order.status),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
                selectinload(Order.customer),
                selectinload(Order.payment),
                selectinload(Order.status_history).selectinload(
                    OrderStatusHistory.status
                ),
            )
            .where(
                Order.store_id == store.id,
                Order.public_id == public_id,
            )
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.tracking_token_hash is not None and not secrets.compare_digest(
            order.tracking_token_hash,
            tracking_token_hash(token),
        ):
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        return order
