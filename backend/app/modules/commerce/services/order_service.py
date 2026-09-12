
# app/modules/commerce/services/order_service.py
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import ensure_utc
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.audit_service import record_audit
from app.modules.commerce.models.cart import Cart
from app.modules.commerce.models.cart_item import CartItem
from app.modules.commerce.models.idempotency_key import IdempotencyKey
from app.modules.commerce.models.inventory_movement import InventoryMovement
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.models.order_status_history import OrderStatusHistory
from app.modules.commerce.models.order_status_transition import OrderStatusTransition
from app.modules.commerce.models.stock_reservation import StockReservation
from app.modules.commerce.notifications import normalize_phone, queue_order_sms
from app.modules.commerce.payment_service import PaymentService
from app.modules.commerce.schemas import CheckoutRequest, OrderStatusUpdate
from app.modules.commerce.services.cart_service import CartService
from app.modules.commerce.services.idempotency import IdempotencyEngine
from app.modules.commerce.tracking import tracking_token, tracking_token_hash
from app.modules.customers.models.customer import Customer
from app.modules.rbac.services.rbac import require_permission


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cart_service = CartService(db)
        self.idempotency = IdempotencyEngine(db)

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

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
                order = await self._load_order_by_public_id(
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

        initial_status = await self._resolve_initial_status()
        subtotal, snapshots = await self._lock_and_verify_catalog(items)
        customer = await self._resolve_checkout_customer(store, payload)

        public_id = secrets.token_hex(16)
        raw_tracking_token = tracking_token(public_id)

        order = Order(
            public_id=public_id,
            store_id=store.id,
            customer_id=customer.id if customer else None,
            status_id=initial_status.id,
            order_number=await self._order_number(),
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
                else normalize_phone(payload.phone) or payload.phone
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

        await self._create_items_and_reservations(
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
                    order = await self._load_order_by_public_id(
                        store.id,
                        existing.resource_public_id,
                    )
                    if order is not None:
                        return order

            raise

        if payment.payment_method.code == "mpesa":
            await self._initiate_mpesa_safely(payment.public_id, order.id)

        return await self._load_order(order.id)

    async def _resolve_initial_status(self) -> OrderStatus:
        statuses = list(
            (
                await self.db.scalars(
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
                detail=(
                    "Order workflow must have exactly one "
                    "active initial status"
                ),
            )

        return statuses[0]

    async def _lock_and_verify_catalog(
        self,
        items: list[CartItem],
    ) -> tuple[int, list[tuple[CartItem, Product, ProductVariant | None, int]]]:
        subtotal = 0
        snapshots: list[
            tuple[CartItem, Product, ProductVariant | None, int]
        ] = []

        for item in items:
            product = await self._lock_product(item.product_id)

            if product.status != "active":
                raise HTTPException(
                    status_code=409,
                    detail=f"{product.name} is no longer available",
                )

            variant = None
            if item.variant_id is not None:
                variant = await self._lock_variant(item.variant_id)

                if (
                    variant is None
                    or variant.product_id != product.id
                    or variant.status != "active"
                ):
                    raise HTTPException(
                        status_code=409,
                        detail=f"{product.name} has an unavailable option",
                    )

            self.cart_service._ensure_stock_available(
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
        self,
        order: Order,
        store: Store,
        snapshots: list[
            tuple[CartItem, Product, ProductVariant | None, int]
        ],
        now: datetime,
    ) -> None:
        reservation_expiry = now + timedelta(
            minutes=settings.payment_reservation_ttl_minutes or 15
        )

        for item, product, variant, unit_price in snapshots:
            label = None
            sku = product.sku

            if variant:
                label = ", ".join(
                    f"{link.option_value.option.name}: "
                    f"{link.option_value.name}"
                    for link in variant.option_value_links
                    if link.option_value and link.option_value.option
                ) or None
                sku = variant.sku or product.sku

            self.db.add(
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
                )
            )

            inventory_owner = variant or product
            if inventory_owner.inventory_tracking:
                self.db.add(
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
        self,
        payment_public_id: str,
        order_id: int,
    ) -> None:
        try:
            await PaymentService(self.db).initiate(payment_public_id)
        except HTTPException as exc:
            payment = await PaymentService(self.db)._load_payment(
                payment_public_id
            )

            if payment is not None and payment.status == "pending":
                payment.status = "failed"
                payment.failure_reason = str(exc.detail)[:1000]
                await self.db.commit()

            await self._release_order_reservations(
                order_id,
                "payment_initiation_failed",
            )
            await self.db.commit()

    # ------------------------------------------------------------------
    # Payment and stock reservations
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Order status and cancellation
    # ------------------------------------------------------------------

    async def update_order_status(
        self,
        user: User,
        tenant_public_id: str,
        public_id: str,
        payload: OrderStatusUpdate,
        idempotency_key: str | None = None,
    ) -> Order:
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

        order = await self._load_order_by_public_id(
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
                previous_order = await self._load_order_by_public_id(
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
            await self._release_order_reservations(
                order.id,
                "order_cancelled",
            )
            await self._restore_cancelled_order_inventory(
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
                    previous_order = await self._load_order_by_public_id(
                        store.id,
                        existing.resource_public_id,
                    )
                    if previous_order is not None:
                        return previous_order

            raise

        return await self._load_order(order.id)

    async def _restore_cancelled_order_inventory(
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
                owner = await self._lock_variant(item.variant_id)
            else:
                owner = await self._lock_product(item.product_id)

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

    # ------------------------------------------------------------------
    # Order queries
    # ------------------------------------------------------------------

    async def list_orders(
        self,
        user: User,
        tenant_public_id: str,
        offset: int,
        limit: int,
        status_public_id: str | None,
    ) -> list[Order]:
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
        store = await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        order = await self._load_order_by_public_id(
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
        store = await resolve_store(
            self.db,
            user,
            tenant_public_id,
            "orders.read",
        )

        order = await self._load_order_by_public_id(
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

        if (
            order.tracking_token_hash is not None
            and not secrets.compare_digest(
                order.tracking_token_hash,
                tracking_token_hash(token),
            )
        ):
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        return order

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_checkout_customer(
        self,
        store: Store,
        payload: CheckoutRequest,
    ) -> Customer | None:
        phone = normalize_phone(payload.phone)

        if not phone:
            return None

        customer = await self.db.scalar(
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
            email=(
                payload.email.strip().lower()
                if payload.email
                else None
            ),
            notes=None,
        )

        try:
            async with self.db.begin_nested():
                self.db.add(customer)
                await self.db.flush()

                await record_audit(
                    self.db,
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
            customer = await self.db.scalar(
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

    async def _order_number(self) -> str:
        for _ in range(8):
            number = secrets.token_hex(6).upper()

            exists = await self.db.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.order_number == number)
            )

            if not exists:
                return number

        raise HTTPException(
            status_code=500,
            detail="Could not allocate an order number",
        )

    async def _lock_product(self, product_id: int) -> Product:
        product = await self.db.scalar(
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
        )

        if product is None:
            raise HTTPException(
                status_code=409,
                detail="A cart item is no longer available",
            )

        return product

    async def _lock_variant(
        self,
        variant_id: int,
    ) -> ProductVariant | None:
        return await self.db.scalar(
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .with_for_update()
        )

    async def _load_order(self, order_id: int) -> Order:
        return await self.db.scalar(
            select(Order)
            .options(
                selectinload(Order.status),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
                selectinload(Order.customer),
            )
            .where(Order.id == order_id)
        )

    async def _load_order_by_public_id(
        self,
        store_id: int,
        public_id: str,
        lock: bool = False,
    ) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.status),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
                selectinload(Order.customer),
            )
            .where(
                Order.store_id == store_id,
                Order.public_id == public_id,
            )
        )

        if lock:
            stmt = stmt.with_for_update()

        return await self.db.scalar(stmt)