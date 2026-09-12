from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.store import Store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.payment import Payment


def phone_digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def phones_match(stored: str, submitted: str) -> bool:
    """Compare phone numbers in a Kenya-friendly way (07… / 254… / +254…)."""
    a = phone_digits(stored)
    b = phone_digits(submitted)
    if not a or not b:
        return False
    if a == b:
        return True

    def canon(digits: str) -> str:
        if digits.startswith("254") and len(digits) >= 12:
            return digits[-9:]
        if digits.startswith("0") and len(digits) >= 10:
            return digits[-9:]
        if len(digits) == 9:
            return digits
        return digits

    return canon(a) == canon(b)


async def lookup_order_by_phone(
    db: AsyncSession,
    store: Store,
    order_number: str,
    phone: str,
) -> Order:
    """Resolve an order for a customer using order number + phone (no tracking token)."""
    number = (order_number or "").strip()
    if not number:
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
    if order is None or not phones_match(order.customer_phone, phone):
        # Same generic error either way — avoid leaking order existence.
        raise HTTPException(status_code=404, detail="Order not found")
    return order
