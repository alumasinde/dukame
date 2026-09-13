# app/modules/commerce/services/order_helpers.py
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import ensure_utc
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.commerce.audit_service import record_audit
from app.modules.commerce.models.cart_item import CartItem
from app.modules.commerce.models.inventory_movement import InventoryMovement
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.stock_reservation import StockReservation
from app.modules.commerce.notifications import normalize_phone
from app.modules.commerce.payment_service import PaymentService
from app.modules.commerce.tracking import tracking_token, tracking_token_hash
from app.modules.customers.models.customer import Customer


async def _resolve_initial_status(db: AsyncSession) -> OrderStatus:
    """Resolve the initial order status for checkout."""
    statuses = list(
        (
            await db.scalars(
                select(OrderStatus)
                .where(
                    OrderStatus.is_initial.is_(True),
                    OrderStatus.is_active.is_(True),
                )
                .order_by(
                    OrderStatus.sort_order.asc(),
                    OrderStatus.id.asc(),
                )
            )
        ).all()
    )

    if len(statuses) != 1:
        raise HTTPException(
            status_code=500,
            detail=("Order workflow must have exactly one " "active initial status"),
        )

    return statuses[0]


async def _lock_and_verify_catalog(
    db: AsyncSession,
    cart_service,
    items: list[CartItem],
) -> tuple[int, list[tuple[CartItem, Product, ProductVariant | None, int]]]:
    """Lock and verify catalog items for checkout."""
    subtotal = 0
    snapshots: list[tuple[CartItem, Product, ProductVariant | None, int]] = []

    for item in items:
        product = await _lock_product(db, item.product_id)

        if product.status != "active":
            raise HTTPException(
                status_code=409,
                detail=f"{product.name} is no longer available",
            )

        variant = None
        if item.variant_id is not None:
            variant = await _lock_variant(db, item.variant_id)

            if (
                variant is None
                or variant.product_id != product.id
                or variant.status != "active"
            ):
                raise HTTPException(
                    status_code=409,
                    detail=f"{product.name} has an unavailable option",
                )

        await cart_service._ensure_stock_available(
            product,
            variant,
            item.quantity,
        )

        unit_price = (
            variant.price_minor
            if variant and variant.price_minor is not None
            else product.price_minor
        )

        subtotal += unit_price * item.quantity
        snapshots.append((item, product, variant, unit_price))

    return subtotal, snapshots


async def _create_items_and_reservations(
    db: AsyncSession,
    order: Order,
    store: Store,
    snapshots: list[tuple[CartItem, Product, ProductVariant | None, int]],
    now: datetime,
) -> None:
    """Create order items and stock reservations."""
    reservation_expiry = now + timedelta(
        minutes=settings.payment_reservation_ttl_minutes or 15
    )

    for item, product, variant, unit_price in snapshots:
        label = None
        sku = product.sku

        if variant:
            label = (
                ", ".join(
                    f"{link.option_value.option.name}: " f"{link.option_value.name}"
                    for link in variant.option_value_links
                    if link.option_value and link.option_value.option
                )
                or None
            )
            sku = variant.sku or product.sku

        db.add(
            OrderItem(
                public_id=secrets.token_hex(16),
                order_id=order.id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                product_name=product.name,
                variant_label=label,
                sku=sku,
                quantity=item.quantity,
                unit_price_minor=unit_price,
                line_total_minor=unit_price * item.quantity,
            )
        )

        inventory_owner = variant or product
        if inventory_owner.inventory_tracking:
            db.add(
                StockReservation(
                    public_id=secrets.token_hex(16),
                    store_id=store.id,
                    order_id=order.id,
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                    quantity=item.quantity,
                    status="pending",
                    expires_at=reservation_expiry,
                )
            )


async def _initiate_mpesa_safely(
    db: AsyncSession,
    payment_public_id: str,
    order_id: int,
    release_reservations_func,
) -> None:
    """Initiate M-Pesa payment with error handling."""
    try:
        await PaymentService(db).initiate(payment_public_id)
    except HTTPException as exc:
        payment = await PaymentService(db)._load_payment(payment_public_id)

        if payment is not None and payment.status == "pending":
            payment.status = "failed"
            payment.failure_reason = str(exc.detail)[:1000]
            await db.commit()

        # Release reservations on payment initiation failure
        await release_reservations_func(order_id, "payment_initiation_failed")
        await db.commit()


async def _resolve_checkout_customer(
    db: AsyncSession,
    store: Store,
    payload,
) -> Customer | None:
    """Resolve or create customer for checkout."""
    from app.modules.commerce.schemas import CheckoutRequest

    phone = normalize_phone(payload.phone)

    if not phone:
        return None

    customer = await db.scalar(
        select(Customer)
        .where(
            Customer.store_id == store.id,
            Customer.phone == phone,
        )
        .with_for_update()
    )

    if customer is not None:
        return customer

    customer = Customer(
        public_id=secrets.token_hex(16),
        store_id=store.id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone=phone,
        email=(payload.email.strip().lower() if payload.email else None),
        notes=None,
    )

    try:
        async with db.begin_nested():
            db.add(customer)
            await db.flush()

            await record_audit(
                db,
                tenant_id=store.tenant_id,
                store_id=store.id,
                actor_user_id=None,
                action="customer.created",
                entity_type="customer",
                entity_public_id=customer.public_id,
                after={
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "is_active": customer.is_active,
                    "source": "checkout",
                },
            )
    except IntegrityError:
        customer = await db.scalar(
            select(Customer)
            .where(
                Customer.store_id == store.id,
                Customer.phone == phone,
            )
            .with_for_update()
        )

        if customer is None:
            raise HTTPException(
                status_code=409,
                detail="Customer could not be associated with this order",
            ) from None

    return customer


async def _order_number(db: AsyncSession) -> str:
    """Generate a unique order number."""
    for _ in range(8):
        number = secrets.token_hex(6).upper()

        exists = await db.scalar(
            select(func.count()).select_from(Order).where(Order.order_number == number)
        )

        if not exists:
            return number

    raise HTTPException(
        status_code=500,
        detail="Could not allocate an order number",
    )


async def _lock_product(db: AsyncSession, product_id: int) -> Product:
    """Lock a product row for update."""
    product = await db.scalar(
        select(Product).where(Product.id == product_id).with_for_update()
    )

    if product is None:
        raise HTTPException(
            status_code=409,
            detail="A cart item is no longer available",
        )

    return product


async def _lock_variant(
    db: AsyncSession,
    variant_id: int,
) -> ProductVariant | None:
    """Lock a variant row for update."""
    return await db.scalar(
        select(ProductVariant).where(ProductVariant.id == variant_id).with_for_update()
    )


async def _load_order(db: AsyncSession, order_id: int) -> Order:
    """Load an order with relationships."""
    return await db.scalar(
        select(Order)
        .options(
            selectinload(Order.status),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.variant),
            selectinload(Order.customer),
            selectinload(Order.payment),
            selectinload(Order.status_history).selectinload(OrderStatusHistory.status),
        )
        .where(Order.id == order_id)
    )


async def _load_order_by_public_id(
    db: AsyncSession,
    store_id: int,
    public_id: str,
    lock: bool = False,
) -> Order | None:
    """Load an order by public ID with optional lock."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.status),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.variant),
            selectinload(Order.customer),
            selectinload(Order.payment),
            selectinload(Order.status_history).selectinload(OrderStatusHistory.status),
        )
        .where(
            Order.store_id == store_id,
            Order.public_id == public_id,
        )
    )

    if lock:
        stmt = stmt.with_for_update()

    return await db.scalar(stmt)
