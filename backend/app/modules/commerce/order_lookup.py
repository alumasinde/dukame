"""Public order lookup helpers for storefront (no auth token)."""
from __future__ import annotations

import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.store import Store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.notification_channels import phone_digits


async def lookup_order_by_phone(
    db: AsyncSession,
    store: Store,
    order_number: str,
    phone: str,
) -> Order:
    """Match store + order number + customer phone. Always 404 on mismatch (privacy)."""
    number = (order_number or "").strip()
    digits = phone_digits(phone or "")
    if not number or len(digits) < 10:
        raise HTTPException(status_code=404, detail="Order not found")

    order = await db.scalar(
        select(Order)
        .options(
            selectinload(Order.status),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.variant),
            selectinload(Order.status_history).selectinload(OrderStatusHistory.status),
            selectinload(Order.payment).selectinload(Payment.payment_method),
        )
        .where(
            Order.store_id == store.id,
            func.lower(Order.order_number) == number.lower(),
        )
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    stored = phone_digits(order.customer_phone or "")
    if not stored or not secrets.compare_digest(stored[-9:], digits[-9:]):
        raise HTTPException(status_code=404, detail="Order not found")
    return order
