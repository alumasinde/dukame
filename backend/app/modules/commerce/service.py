from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.auth.models.identity import User
from app.modules.catalogue.models.option_value import ProductOptionValue
from app.modules.catalogue.models.product import Product
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue
from app.modules.catalogue.models.store import Store
from app.modules.catalogue.services.context import resolve_store
from app.modules.commerce.models.cart import Cart
from app.modules.commerce.models.cart_item import CartItem
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_item import OrderItem
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.schemas import CartItemAdd, CartItemUpdate, CheckoutRequest, OrderStatusUpdate


class CommerceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _ensure_tz_aware(dt: datetime | None) -> datetime | None:
        """Ensure datetime is timezone-aware, converting if necessary."""
        if dt is None:
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    async def get_or_create_cart(self, store: Store, token: str | None) -> tuple[Cart, str, bool]:
        if token:
            cart = await self._cart_by_token(store.id, token, lock=False)
            now = datetime.now(UTC)
            if cart is not None and cart.checked_out_at is None:
                expires_at = self._ensure_tz_aware(cart.expires_at)
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
        cart = await self._load_cart(cart.id)
        return cart

    async def add_item(self, store: Store, token: str, payload: CartItemAdd) -> Cart:
        self._ensure_quantity(payload.quantity)
        cart = await self._require_cart(store.id, token)
        product = await self._product_for_cart(store.id, payload.product_public_id)
        variant = await self._resolve_variant(store.id, product, payload.variant_public_id)
        unit_price = variant.price_minor if variant and variant.price_minor is not None else product.price_minor
        existing = await self.db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id, CartItem.variant_id == (variant.id if variant else None)))
        new_quantity = (existing.quantity if existing else 0) + payload.quantity
        self._ensure_quantity(new_quantity)
        self._ensure_stock(product, variant, new_quantity)
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
        self._ensure_stock(item.product, item.variant, payload.quantity)
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

    async def checkout(self, store: Store, token: str, payload: CheckoutRequest) -> Order:
        cart = await self._cart_by_token(store.id, token, lock=True)
        now = datetime.now(UTC)
        expires_at = self._ensure_tz_aware(cart.expires_at) if cart else None
        if cart is None or cart.checked_out_at is not None or expires_at is None or expires_at <= now:
            raise HTTPException(status_code=409, detail="Your cart has expired. Please start a new cart.")
        items = list((await self.db.scalars(select(CartItem).options(selectinload(CartItem.product).selectinload(Product.media), selectinload(CartItem.variant).selectinload(ProductVariant.option_value_links).selectinload(ProductVariantOptionValue.option_value).selectinload(ProductOptionValue.option)).where(CartItem.cart_id == cart.id).with_for_update())).all())
        if not items:
            raise HTTPException(status_code=422, detail="Your cart is empty")
        initial_status = await self.db.scalar(select(OrderStatus).where(OrderStatus.is_initial.is_(True), OrderStatus.is_active.is_(True)).order_by(OrderStatus.sort_order.asc(), OrderStatus.id.asc()).limit(1))
        if initial_status is None:
            raise HTTPException(status_code=500, detail="No initial order status is configured")
        subtotal = 0
        snapshots: list[tuple[CartItem, Product, ProductVariant | None, int]] = []
        for item in items:
            product = await self._lock_product(item.product.id)
            if product.status != "active":
                raise HTTPException(status_code=409, detail=f"{product.name} is no longer available")
            variant = None
            if item.variant_id is not None:
                variant = await self._lock_variant(item.variant_id)
                if variant is None or variant.product_id != product.id or variant.status != "active":
                    raise HTTPException(status_code=409, detail=f"{product.name} has an unavailable option")
            self._ensure_stock(product, variant, item.quantity)
            unit_price = variant.price_minor if variant and variant.price_minor is not None else product.price_minor
            subtotal += unit_price * item.quantity
            snapshots.append((item, product, variant, unit_price))
        order = Order(public_id=secrets.token_hex(16), store_id=store.id, status_id=initial_status.id, order_number=await self._order_number(), customer_first_name=payload.first_name.strip(), customer_last_name=payload.last_name.strip(), customer_email=payload.email.strip() if payload.email else None, customer_phone=payload.phone.strip(), notes=payload.notes.strip() if payload.notes else None, currency=store.currency, subtotal_minor=subtotal, total_minor=subtotal)
        self.db.add(order)
        await self.db.flush()
        for item, product, variant, unit_price in snapshots:
            label = None
            sku = product.sku
            if variant:
                label = ", ".join(f"{link.option_value.option.name}: {link.option_value.name}" for link in variant.option_value_links if link.option_value and link.option_value.option) or None
                sku = variant.sku or product.sku
            self.db.add(OrderItem(public_id=secrets.token_hex(16), order_id=order.id, product_id=product.id, variant_id=variant.id if variant else None, product_name=product.name, variant_label=label, sku=sku, quantity=item.quantity, unit_price_minor=unit_price, line_total_minor=unit_price * item.quantity))
            inventory_owner = variant or product
            if inventory_owner.inventory_tracking:
                inventory_owner.inventory_quantity -= item.quantity
        cart.checked_out_at = datetime.now(UTC)
        await self.db.commit()
        return await self._load_order(order.id)

    async def list_orders(self, user: User, tenant_public_id: str, offset: int, limit: int, status_public_id: str | None):
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        stmt = select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant)).where(Order.store_id == store.id).order_by(Order.created_at.desc(), Order.id.desc()).offset(offset).limit(limit)
        if status_public_id:
            stmt = stmt.join(Order.status).where(OrderStatus.public_id == status_public_id)
        return list((await self.db.scalars(stmt)).unique().all())

    async def get_order(self, user: User, tenant_public_id: str, public_id: str) -> Order:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.read")
        order = await self._load_order_by_public_id(store.id, public_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def update_order_status(self, user: User, tenant_public_id: str, public_id: str, payload: OrderStatusUpdate) -> Order:
        store = await resolve_store(self.db, user, tenant_public_id, "orders.status.manage")
        order = await self._load_order_by_public_id(store.id, public_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status.is_terminal:
            raise HTTPException(status_code=409, detail="A completed or cancelled order cannot be changed")
        status = await self.db.scalar(select(OrderStatus).where(OrderStatus.public_id == payload.status_public_id, OrderStatus.is_active.is_(True)))
        if status is None:
            raise HTTPException(status_code=422, detail="Order status not found")
        order.status_id = status.id
        await self.db.commit()
        return await self._load_order(order.id)

    async def list_statuses(self, user: User, tenant_public_id: str):
        await resolve_store(self.db, user, tenant_public_id, "orders.read")
        return list((await self.db.scalars(select(OrderStatus).where(OrderStatus.is_active.is_(True)).order_by(OrderStatus.sort_order, OrderStatus.id))).all())

    async def _require_cart(self, store_id: int, token: str) -> Cart:
        cart = await self._cart_by_token(store_id, token, lock=True)
        now = datetime.now(UTC)
        expires_at = self._ensure_tz_aware(cart.expires_at) if cart else None
        if cart is None or cart.checked_out_at is not None or expires_at is None or expires_at <= now:
            raise HTTPException(status_code=409, detail="Your cart has expired. Please start a new cart.")
        return cart

    async def _cart_by_token(self, store_id: int, token: str, lock: bool) -> Cart | None:
        stmt = select(Cart).where(Cart.store_id == store_id, Cart.session_token_hash == self._hash_token(token))
        if lock:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def _load_cart(self, cart_id: int) -> Cart:
        return await self.db.scalar(select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product).selectinload(Product.media), selectinload(Cart.items).selectinload(CartItem.variant).selectinload(ProductVariant.option_value_links).selectinload(ProductVariantOptionValue.option_value).selectinload(ProductOptionValue.option)).where(Cart.id == cart_id))

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

    @staticmethod
    def _ensure_stock(product: Product, variant: ProductVariant | None, quantity: int) -> None:
        inventory_owner = variant or product
        if inventory_owner.inventory_tracking and inventory_owner.inventory_quantity < quantity:
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
        return await self.db.scalar(select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant)).where(Order.id == order_id))

    async def _load_order_by_public_id(self, store_id: int, public_id: str) -> Order | None:
        return await self.db.scalar(select(Order).options(selectinload(Order.status), selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.items).selectinload(OrderItem.variant)).where(Order.store_id == store_id, Order.public_id == public_id))

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
