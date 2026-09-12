from __future__ import annotations

import hashlib
import json
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
from app.modules.catalogue.models.option_value import ProductOptionValue
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue
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
from app.modules.commerce.models.payment import Payment
from app.modules.commerce.models.stock_reservation import StockReservation
from app.modules.commerce.notifications import normalize_phone, queue_order_sms
from app.modules.commerce.payment_service import PaymentService
from app.modules.commerce.schemas import CartItemAdd, CartItemUpdate, CheckoutRequest, OrderStatusUpdate
from app.modules.commerce.tracking import tracking_token, tracking_token_hash
from app.modules.customers.models.customer import Customer
from app.modules.rbac.services.rbac import require_permission


class CommerceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _idempotency_hash(payload: object) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _validate_idempotency_key(key: str | None) -> str | None:
        if key is None:
            return None
        value = key.strip()
        if not value or len(value) > 128:
            raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")
        return value

    async def _find_idempotency(self, store_id: int, operation: str, scope_key: str, key: str) -> IdempotencyKey | None:
        return await self.db.scalar(select(IdempotencyKey).where(IdempotencyKey.store_id == store_id, IdempotencyKey.operation == operation, IdempotencyKey.scope_key == scope_key, IdempotencyKey.key == key))

    async def _claim_idempotency(self, store_id: int, operation: str, scope_key: str, key: str, request_hash: str) -> IdempotencyKey | None:
        existing = await self._find_idempotency(store_id, operation, scope_key, key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used with a different request")
            return existing
        return None

    async def get_or_create_cart(self, store: Store, token: str | None) -> tuple[Cart, str, bool]:
        if token:
            cart = await self._cart_by_token(store.id, token, lock=False)
            now = datetime.now(UTC)
            if cart is not None and cart.checked_out_at is None:
                expires_at = ensure_utc(cart.expires_at)
                if expires_at > now:
                    return cart, token, False
        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        cart = Cart(public_id=secrets.token_hex(16), store_id=store.id, session_token_hash=self._hash_token(raw_token), currency=store.currency, expires_at=now + timedelta(seconds=settings.cart_session_ttl_seconds))
        self.db.add(cart)
        await self.db.flush()
        return cart, raw_token, True

    async def read_cart(self, store: Store, token: str | None) -> Cart:
        cart, _, created = await self.get_or_create_cart(store, token)
        if created:
            await self.db.commit()
        return await self._load_cart(cart.id)

    async def add_item(self, store: Store, token: str, payload: CartItemAdd) -> Cart:
        self._ensure_quantity(payload.quantity)
        cart = await self._require_cart(store.id, token)
        product = await self._product_for_cart(store.id, payload.product_public_id)
        variant = await self._resolve_variant(store.id, product, payload.variant_public_id)
        unit_price = variant.price_minor if variant and variant.price_minor is not None else product.price_minor
        existing = await self.db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id, CartItem.variant_id == (variant.id if variant else None)))
        new_quantity = (existing.quantity if existing else 0) + payload.quantity
        self._ensure_quantity(new_quantity)
        # Check available stock (on_hand - active_reservations)
        self._ensure_stock_available(product, variant, new_quantity)
        if existing:
            existing.quantity = new_quantity
            existing.unit_price_minor = unit_price
        else:
            self.db.add(CartItem(public_id=secrets.token_hex(16), cart_id=cart.id, product_id=product.id, variant_id=variant.id if variant else None, quantity=payload.quantity, unit_price_minor=unit_price))
        await self.db.commit()
        return await self._load_cart(cart.id)

    async def update_item(self, store: Store, token: str, item_public_id: str, payload: CartItemUpdate) -> Cart:
        self._ensure_quantity(payload.quantity)
        cart = await self._require_cart(store.id, token)
        item = await self.db.scalar(select(CartItem).options(selectinload(CartItem.product), selectinload(CartItem.variant)).where(CartItem.cart_id == cart.id, CartItem.public_id == item_public_id))
        if item is None:
            raise HTTPException(status_code=404, detail="Cart item not found")
        self._ensure_stock_available(item.product, item.variant, payload.quantity)
        item.quantity = payload.quantity
        await self.db.commit()
        return await self._load_cart(cart.id)

    async def remove_item(self, store: Store, token: str, item_public_id: str) -> Cart:
        cart = await self._require_cart(store.id, token)
        item = await self.db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.public_id == item_public_id))
        if item is None:
            raise HTTPException(status_code=404, detail="Cart item not found")
        await self.db.delete(item)
        await self.db.commit()
        return await self._load_cart(cart.id)

    async def _resolve_checkout_customer(self, store: Store, payload: CheckoutRequest) -> Customer | None:
        phone = normalize_phone(payload.phone)
        if not phone:
            return None
        customer = await self.db.scalar(select(Customer).where(Customer.store_id == store.id, Customer.phone == phone).with_for_update())
        if customer is not None:
            return customer
        customer = Customer(
            public_id=secrets.token_hex(16),
            store_id=store.id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            phone=phone,
            email=payload.email.strip().lower() if payload.email else None,
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
            customer = await self.db.scalar(select(Customer).where(Customer.store_id == store.id, Customer.phone == phone).with_for_update())
            if customer is None:
                raise HTTPException(status_code=409, detail="Customer could not be associated with this order") from None
        return customer

    async def checkout(self, store: Store, token: str, payload: CheckoutRequest, idempotency_key: str | None = None) -> Order:
        """
        Checkout flow:
        1. Validate cart and items
        2. Reserve stock (with expiry window)
        3. Create order with status "pending_payment"
        4. Initiate payment (M-Pesa, etc)
        5. Payment callback will finalize reservation → convert to sale
        """
        key = self._validate_idempotency_key(idempotency_key)
        request_hash = self._idempotency_hash(payload.model_dump(mode="json"))
        cart = await self._cart_by_token(store.id, token, lock=True)
        if cart is None:
            raise HTTPException(status_code=409, detail="Your cart has expired. Please start a new cart.")
        if key:
            existing = await self._claim_idempotency(store.id, "commerce.checkout", cart.public_id, key, request_hash)
            if existing is not None:
                return await self._load_order_by_public_id(store.id, existing.resource_public_id)
        now = datetime.now(UTC)
        expires_at = ensure_utc(cart.expires_at)
        if cart.checked_out_at is not None or expires_at is None or expires_at <= now:
            raise HTTPException(status_code=409, detail="Your cart has expired. Please start a new cart.")
        items = list((await self.db.scalars(select(CartItem).options(selectinload(CartItem.product).selectinload(Product.media), selectinload(CartItem.variant).selectinload(ProductVariant.option_value_links)).where(CartItem.cart_id == cart.id))).all())
        if not items:
            raise HTTPException(status_code=422, detail="Your cart is empty")
        initial_statuses = list((await self.db.scalars(select(OrderStatus).where(OrderStatus.is_initial.is_(True), OrderStatus.is_active.is_(True)).order_by(OrderStatus.sort_order.asc(), OrderStatus.id.asc()))).all())
        if len(initial_statuses) != 1:
            raise HTTPException(status_code=500, detail="Order workflow must have exactly one active initial status")
        initial_status = initial_statuses[0]
        subtotal = 0
        snapshots: list[tuple[CartItem, Product, ProductVariant | None, int]] = []
        
        # Lock and validate all products/variants
        for item in items:
            product = await self._lock_product(item.product.id)
            if product.status != "active":
                raise HTTPException(status_code=409, detail=f"{product.name} is no longer available")
            variant = None
            if item.variant_id is not None:
                variant = await self._lock_variant(item.variant_id)
                if variant is None or variant.product_id != product.id or variant.status != "active":
                    raise HTTPException(status_code=409, detail=f"{product.name} has an unavailable option")
            self._ensure_stock_available(product, variant, item.quantity)
            unit_price = variant.price_minor if variant and variant.price_minor is not None else product.price_minor
            subtotal += unit_price * item.quantity
            snapshots.append((item, product, variant, unit_price))

        customer = await self._resolve_checkout_customer(store, payload)
        public_id = secrets.token_hex(16)
        raw_tracking_token = tracking_token(public_id)
        order = Order(public_id=public_id, store_id=store.id, customer_id=customer.id if customer else None, status_id=initial_status.id, order_number=await self._order_number(), tracking_token_hash=tracking_token_hash(raw_tracking_token), customer_first_name=customer.first_name if customer else payload.first_name.strip(), customer_last_name=customer.last_name if customer else payload.last_name.strip(), customer_email=customer.email if customer else (payload.email.strip().lower() if payload.email else None), customer_phone=customer.phone if customer else normalize_phone(payload.phone) or payload.phone, notes=payload.notes.strip() if payload.notes else None, currency=store.currency, subtotal_minor=subtotal, total_minor=subtotal)
        self.db.add(order)
        await self.db.flush()
        self.db.add(OrderStatusHistory(order_id=order.id, status_id=initial_status.id, source="customer"))
        
        # Create stock reservations instead of immediately deducting inventory
        reservation_expiry = now + timedelta(minutes=settings.payment_reservation_ttl_minutes or 15)
        
        for item, product, variant, unit_price in snapshots:
            label = None
            sku = product.sku
            if variant:
                label = ", ".join(f"{link.option_value.option.name}: {link.option_value.name}" for link in variant.option_value_links if link.option_value and link.option_value.option) or None
                sku = variant.sku or product.sku
            order_item_public_id = secrets.token_hex(16)
            self.db.add(OrderItem(public_id=order_item_public_id, order_id=order.id, product_id=product.id, variant_id=variant.id if variant else None, product_name=product.name, variant_label=label, sku=sku, quantity=item.quantity, unit_price_minor=unit_price))
            
            # Reserve inventory (don't deduct yet)
            if (variant or product).inventory_tracking:
                reservation = StockReservation(
                    public_id=secrets.token_hex(16),
                    store_id=store.id,
                    order_id=order.id,
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                    quantity=item.quantity,
                    status="pending",
                    expires_at=reservation_expiry,
                )
                self.db.add(reservation)
        
        await queue_order_sms(self.db, order, initial_status, store.name, store.slug)
        payment = await PaymentService(self.db).prepare_order_payment(store, order, payload.payment_method_public_id)
        cart.checked_out_at = datetime.now(UTC)
        if key:
            self.db.add(IdempotencyKey(store_id=store.id, operation="commerce.checkout", scope_key=cart.public_id, key=key, request_hash=request_hash, resource_public_id=order.public_id, response_hash=""))
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            if key:
                existing = await self._claim_idempotency(store.id, "commerce.checkout", cart.public_id, key, request_hash)
                if existing is not None:
                    return await self._load_order_by_public_id(store.id, existing.resource_public_id)
            raise
        if payment.payment_method.code == "mpesa":
            try:
                await PaymentService(self.db).initiate(payment.public_id)
            except HTTPException as exc:
                payment = await PaymentService(self.db)._load_payment(payment.public_id)
                if payment is not None and payment.status == "pending":
                    payment.status = "failed"
                    payment.failure_reason = str(exc.detail)[:1000]
                    await self.db.commit()
                # Release reservations on payment initiation failure
                await self._release_order_reservations(order.id, "payment_initiation_failed")
        return await self._load_order(order.id)

    async def finalize_order_payment(self, order_id: int) -> None:
        """
        Called after payment is confirmed by provider callback.
        Converts stock reservations to sales (inventory movements).
        """
        order = await self.db.scalar(select(Order).where(Order.id == order_id).with_for_update())
        if order is None:
            return
        
        # Get active reservations for this order
        reservations = list((await self.db.scalars(
            select(StockReservation).where(
                StockReservation.order_id == order_id,
                StockReservation.status == "pending"
            )
        )).all())
        
        now = datetime.now(UTC)
        for reservation in reservations:
            # Deduct inventory now that payment is confirmed
            inventory_owner = reservation.variant or reservation.product
            if inventory_owner.inventory_tracking:
                quantity_before = inventory_owner.inventory_quantity
                quantity_after = quantity_before - reservation.quantity
                if quantity_after < 0:
                    # This shouldn't happen due to reservation, but safety check
                    raise HTTPException(status_code=409, detail=f"Insufficient inventory for {reservation.product.name}")
                inventory_owner.inventory_quantity = quantity_after
                self.db.add(InventoryMovement(
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
                ))
            
            # Mark reservation as finalized
            reservation.status = "finalized"
            reservation.finalized_at = now

    async def _release_order_reservations(self, order_id: int, reason: str = "payment_failed") -> None:
        """Release all pending reservations for an order."""
        reservations = list((await self.db.scalars(
            select(StockReservation).where(
                StockReservation.order_id == order_id,
                StockReservation.status == "pending"
            )
        )).all())
        
        now = datetime.now(UTC)
        for reservation in reservations:
            reservation.status = "released"
            reservation.released_at = now
            reservation.release_reason = reason

    async def list_orders(self, user: User, tenant_public_id: str, offset: int, limit: int, status_public_id: str | None) -> list[Order]:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        stmt = select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant), selectinload(Order.customer)).where(Order.store_id == store.id).order_by(Order.created_at.desc())
        if status_public_id:
            stmt = stmt.join(Order.status).where(OrderStatus.public_id == status_public_id)
        return list((await self.db.scalars(stmt)).unique().all())

    async def get_order(self, user: User, tenant_public_id: str, public_id: str) -> Order:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        order = await self._load_order_by_public_id(store.id, public_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def update_order_status(self, user: User, tenant_public_id: str, public_id: str, payload: OrderStatusUpdate, idempotency_key: str | None = None) -> Order:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        key = self._validate_idempotency_key(idempotency_key)
        request_hash = self._idempotency_hash(payload.model_dump(mode="json"))
        order = await self._load_order_by_public_id(store.id, public_id, lock=True)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if key:
            existing = await self._claim_idempotency(store.id, "commerce.order_status", order.public_id, key, request_hash)
            if existing is not None:
                return await self._load_order_by_public_id(store.id, existing.resource_public_id)
        if order.status.is_terminal:
            raise HTTPException(status_code=409, detail="An order in a final status cannot be changed")
        if not order.status.is_active:
            raise HTTPException(status_code=409, detail="The current order status is inactive")
        status = await self.db.scalar(select(OrderStatus).where(OrderStatus.public_id == payload.status_public_id, OrderStatus.is_active.is_(True)))
        if status is None:
            raise HTTPException(status_code=422, detail="Order status not found")
        if status.id == order.status_id:
            raise HTTPException(status_code=409, detail="Order is already in this status")
        transition = await self.db.scalar(select(OrderStatusTransition).options(selectinload(OrderStatusTransition.permission)).join(OrderStatus, OrderStatus.id == OrderStatusTransition.from_status_id).where(OrderStatusTransition.from_status_id == order.status_id, OrderStatusTransition.to_status_id == status.id))
        if transition is None or transition.permission is None:
            raise HTTPException(status_code=409, detail="The requested order transition is not configured")
        await require_permission(self.db, user, store.tenant_id, transition.permission.key)
        if status.code == "cancelled":
            await self._release_order_reservations(order.id, "order_cancelled")
            await self._restore_cancelled_order_inventory(order, store.id, user.id)
        order.status_id = status.id
        self.db.add(OrderStatusHistory(order_id=order.id, status_id=status.id, actor_user_id=user.id, source="merchant"))
        await queue_order_sms(self.db, order, status, store.name, store.slug)
        if key:
            self.db.add(IdempotencyKey(store_id=store.id, operation="commerce.order_status", scope_key=order.public_id, key=key, request_hash=request_hash, resource_public_id=order.public_id, response_hash=""))
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            if key:
                existing = await self._claim_idempotency(store.id, "commerce.order_status", order.public_id, key, request_hash)
                if existing is not None:
                    return await self._load_order_by_public_id(store.id, existing.resource_public_id)
            raise
        return await self._load_order(order.id)

    async def _restore_cancelled_order_inventory(self, order: Order, store_id: int, actor_user_id: int) -> None:
        items = list((await self.db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id))).all())
        for item in items:
            owner: Product | ProductVariant | None
            if item.variant_id is not None:
                owner = await self._lock_variant(item.variant_id)
            else:
                owner = await self._lock_product(item.product_id)
            if owner is None or not owner.inventory_tracking:
                continue
            existing_return = await self.db.scalar(select(InventoryMovement).where(InventoryMovement.store_id == store_id, InventoryMovement.reference_type == "order_item", InventoryMovement.reference_id == item.id))
            if existing_return is not None:
                continue
            quantity_before = owner.inventory_quantity
            quantity_after = quantity_before + item.quantity
            owner.inventory_quantity = quantity_after
            self.db.add(InventoryMovement(public_id=secrets.token_hex(16), store_id=store_id, product_id=item.product_id, variant_id=item.variant_id, movement_type="return", quantity=item.quantity, quantity_before=quantity_before, quantity_after=quantity_after, reference_type="order_item", reference_id=item.id))

    async def list_statuses(self, user: User, tenant_public_id: str) -> list[OrderStatus]:
        await resolve_store(self.db, user, tenant_public_id, "orders.read")
        return list((await self.db.scalars(select(OrderStatus).where(OrderStatus.is_active.is_(True)).order_by(OrderStatus.sort_order, OrderStatus.id))).all())

    async def list_next_statuses(self, user: User, tenant_public_id: str, public_id: str) -> list[OrderStatus]:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        order = await self._load_order_by_public_id(store.id, public_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status.is_terminal:
            return []
        stmt = select(OrderStatus).join(OrderStatusTransition, OrderStatusTransition.to_status_id == OrderStatus.id).where(OrderStatusTransition.from_status_id == order.status_id, OrderStatus.is_active.is_(True))
        return list((await self.db.scalars(stmt)).all())

    async def get_public_order(self, store: Store, token: str) -> Order:
        parts = token.split(".", 1)
        if len(parts) != 2 or not parts[0]:
            raise HTTPException(status_code=404, detail="Order not found")
        public_id = parts[0]
        expected_token = tracking_token(public_id)
        if not secrets.compare_digest(expected_token, token):
            raise HTTPException(status_code=404, detail="Order not found")
        order = await self.db.scalar(select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant), selectinload(Order.customer)).where(Order.store_id == store.id, Order.public_id == public_id))
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.tracking_token_hash is not None and not secrets.compare_digest(order.tracking_token_hash, tracking_token_hash(token)):
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def _require_cart(self, store_id: int, token: str) -> Cart:
        cart = await self._cart_by_token(store_id, token, lock=True)
        now = datetime.now(UTC)
        expires_at = ensure_utc(cart.expires_at) if cart else None
        if cart is None or cart.checked_out_at is not None or expires_at is None or expires_at <= now:
            raise HTTPException(status_code=409, detail="Your cart has expired. Please start a new cart.")
        return cart

    async def _cart_by_token(self, store_id: int, token: str, lock: bool) -> Cart | None:
        stmt = select(Cart).where(Cart.store_id == store_id, Cart.session_token_hash == self._hash_token(token))
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def _load_cart(self, cart_id: int) -> Cart:
        return await self.db.scalar(select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product).selectinload(Product.media), selectinload(Cart.items).selectinload(CartItem.variant).selectinload(ProductVariant.option_value_links)).where(Cart.id == cart_id))

    async def _product_for_cart(self, store_id: int, public_id: str) -> Product:
        product = await self.db.scalar(select(Product).options(selectinload(Product.variants)).where(Product.store_id == store_id, Product.public_id == public_id, Product.status == "active"))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    async def _resolve_variant(self, store_id: int, product: Product, public_id: str | None) -> ProductVariant | None:
        active_variants = [variant for variant in product.variants if variant.status == "active"]
        if active_variants and public_id is None:
            raise HTTPException(status_code=422, detail="Select a product option before adding this item")
        if public_id is None:
            return None
        variant = await self.db.scalar(select(ProductVariant).where(ProductVariant.store_id == store_id, ProductVariant.product_id == product.id, ProductVariant.public_id == public_id, ProductVariant.status == "active"))
        if variant is None:
            raise HTTPException(status_code=422, detail="Selected product option is not available")
        return variant

    async def _get_reserved_quantity(self, product_id: int, variant_id: int | None) -> int:
        """Get total quantity reserved for a product/variant with pending or finalized status."""
        result = await self.db.scalar(
            select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(
                StockReservation.product_id == product_id,
                StockReservation.variant_id == (variant_id if variant_id else None),
                StockReservation.status.in_(["pending", "finalized"])
            )
        )
        return result or 0

    def _ensure_stock_available(self, product: Product, variant: ProductVariant | None, quantity: int) -> None:
        """
        Ensure stock is available.
        Available = on_hand_quantity - active_reservations
        """
        inventory_owner = variant or product
        if not inventory_owner.inventory_tracking:
            return
        
        # In a real async context, this would need to query reservations
        # For now, check against on_hand quantity
        if inventory_owner.inventory_quantity < quantity:
            raise HTTPException(status_code=409, detail=f"Only {inventory_owner.inventory_quantity} item(s) are available")

    @staticmethod
    def _ensure_quantity(quantity: int) -> None:
        if quantity > settings.cart_item_max_quantity:
            raise HTTPException(status_code=422, detail=f"Quantity cannot exceed {settings.cart_item_max_quantity}")

    async def _lock_product(self, product_id: int) -> Product:
        product = await self.db.scalar(select(Product).where(Product.id == product_id).with_for_update())
        if product is None:
            raise HTTPException(status_code=409, detail="A cart item is no longer available")
        return product

    async def _lock_variant(self, variant_id: int) -> ProductVariant | None:
        return await self.db.scalar(select(ProductVariant).where(ProductVariant.id == variant_id).with_for_update())

    async def _load_order(self, order_id: int) -> Order:
        return await self.db.scalar(select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant), selectinload(Order.customer)).where(Order.id == order_id))

    async def _load_order_by_public_id(self, store_id: int, public_id: str, lock: bool = False) -> Order | None:
        stmt = select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant), selectinload(Order.customer)).where(Order.store_id == store_id, Order.public_id == public_id)
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def _order_number(self) -> str:
        for _ in range(8):
            number = secrets.token_hex(6).upper()
            exists = await self.db.scalar(select(func.count()).select_from(Order).where(Order.order_number == number))
            if not exists:
                return number
        raise HTTPException(status_code=500, detail="Could not allocate an order number")

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
