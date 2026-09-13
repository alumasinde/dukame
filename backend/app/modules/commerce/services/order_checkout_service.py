# app/modules/commerce/services/order_checkout_service.py
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import ensure_utc
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.commerce.models.cart import Cart
from app.modules.commerce.models.cart_item import CartItem
from app.modules.commerce.models.idempotency_key import IdempotencyKey
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.stock_reservation import StockReservation
from app.modules.commerce.notifications import queue_order_sms
from app.modules.commerce.payment_service import PaymentService
from app.modules.commerce.schemas import CheckoutRequest
from app.modules.commerce.services.cart_service import CartService
from app.modules.commerce.services.idempotency import IdempotencyEngine
from app.modules.commerce.tracking import tracking_token, tracking_token_hash
from app.modules.customers.models.customer import Customer
from app.modules.commerce.services.order_helpers import (
    _create_items_and_reservations,
    _initiate_mpesa_safely,
    _lock_and_verify_catalog,
    _lock_product,
    _lock_variant,
    _load_order,
    _load_order_by_public_id,
    _order_number,
    _resolve_checkout_customer,
    _resolve_initial_status,
)


class OrderCheckoutService:
    """Handles order checkout and order creation logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cart_service = CartService(db)
        self.idempotency = IdempotencyEngine(db)

    async def checkout(
        self,
        store: Store,
        token: str,
        payload: CheckoutRequest,
        idempotency_key: str | None = None,
    ) -> Order:
        """
        Create an order and pending stock reservations.

        Inventory is not deducted here. It is deducted when payment is
        confirmed and finalize_order_payment() is called.
        """
        key = self.idempotency.validate_key(idempotency_key)
        request_hash = self.idempotency.calculate_hash(
            payload.model_dump(mode="json")
        )

        # Keep the cart locked while checking out.
        # Do not use require_cart() here: an idempotent retry must still be
        # able to retrieve its order after the cart has been checked out.
        cart = await self.cart_service._cart_by_token(
            store.id,
            token,
            lock=True,
        )

        if cart is None:
            raise HTTPException(
                status_code=409,
                detail="Your cart has expired. Please start a new cart.",
            )

        if key:
            existing = await self.idempotency.claim_key(
                store.id,
                "commerce.checkout",
                cart.public_id,
                key,
                request_hash,
            )
            if existing is not None:
                order = await _load_order_by_public_id(
                    self.db,
                    store.id,
                    existing.resource_public_id,
                )
                if order is None:
                    raise HTTPException(
                        status_code=409,
                        detail="The previous checkout order could not be found.",
                    )
                return order

        now = datetime.now(UTC)
        expires_at = ensure_utc(cart.expires_at)

        if (
            cart.checked_out_at is not None
            or expires_at is None
            or expires_at <= now
        ):
            raise HTTPException(
                status_code=409,
                detail="Your cart has expired. Please start a new cart.",
            )

        items = list(
            (
                await self.db.scalars(
                    select(CartItem)
                    .options(
                        selectinload(CartItem.product).selectinload(Product.media),
                        selectinload(CartItem.variant).selectinload(
                            ProductVariant.option_value_links
                        ),
                    )
                    .where(CartItem.cart_id == cart.id)
                )
            ).all()
        )

        if not items:
            raise HTTPException(
                status_code=422,
                detail="Your cart is empty",
            )

        initial_status = await _resolve_initial_status(self.db)
        subtotal, snapshots = await _lock_and_verify_catalog(
            self.db,
            self.cart_service,
            items
        )
        customer = await _resolve_checkout_customer(
            self.db,
            store,
            payload
        )

        public_id = secrets.token_hex(16)
        raw_tracking_token = tracking_token(public_id)

        order = Order(
            public_id=public_id,
            store_id=store.id,
            customer_id=customer.id if customer else None,
            status_id=initial_status.id,
            order_number=await _order_number(self.db),
            tracking_token_hash=tracking_token_hash(raw_tracking_token),
            customer_first_name=(
                customer.first_name
                if customer
                else payload.first_name.strip()
            ),
            customer_last_name=(
                customer.last_name
                if customer
                else payload.last_name.strip()
            ),
            customer_email=(
                customer.email
                if customer
                else (
                    payload.email.strip().lower()
                    if payload.email
                    else None
                )
            ),
            customer_phone=(
                customer.phone
                if customer
                else payload.phone
            ),
            delivery_address=payload.delivery_address.strip(),
            delivery_landmark=payload.delivery_landmark.strip() if payload.delivery_landmark else None,
            delivery_notes=payload.delivery_notes.strip() if payload.delivery_notes else None,
            delivery_option=payload.delivery_option or "standard",
            notes=payload.notes.strip() if payload.notes else None,
            currency=store.currency,
            subtotal_minor=subtotal,
            total_minor=subtotal,
        )

        self.db.add(order)
        await self.db.flush()

        self.db.add(
            OrderStatusHistory(
                order_id=order.id,
                status_id=initial_status.id,
                source="customer",
            )
        )

        await _create_items_and_reservations(
            self.db,
            order,
            store,
            snapshots,
            now,
        )

        await queue_order_sms(
            self.db,
            order,
            initial_status,
            store.name,
            store.slug,
        )

        payment = await PaymentService(self.db).prepare_order_payment(
            store,
            order,
            payload.payment_method_public_id,
        )

        cart.checked_out_at = now

        if key:
            self.db.add(
                IdempotencyKey(
                    store_id=store.id,
                    operation="commerce.checkout",
                    scope_key=cart.public_id,
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
                    "commerce.checkout",
                    cart.public_id,
                    key,
                    request_hash,
                )
                if existing is not None:
                    order = await _load_order_by_public_id(
                        self.db,
                        store.id,
                        existing.resource_public_id,
                    )
                    if order is not None:
                        return order

            raise

        if payment.payment_method.code == "mpesa":
            # Import here to avoid circular dependency
            from app.modules.commerce.services.order_inventory_service import (
                OrderInventoryService,
            )
            inventory_service = OrderInventoryService(self.db)
            await _initiate_mpesa_safely(
                self.db,
                payment.public_id,
                order.id,
                inventory_service._release_order_reservations
            )

        return await _load_order(self.db, order.id)