from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.catalogue.models.variant import ProductVariant
from app.modules.catalogue.models.store import Store
from app.modules.commerce.models.cart import Cart
from app.modules.commerce.models.order import Order
from app.modules.commerce.payment_service import PaymentService, payment_response
from app.modules.commerce.schemas import CartItemAdd, CartItemUpdate, CartResponse, CheckoutRequest, OrderLookupRequest, OrderResponse, OrderStatusHistoryResponse, OrderStatusResponse, OrderTrackingResponse, PaymentResponse
from app.modules.commerce.service import CommerceService
from app.modules.commerce.tracking import tracking_token as make_tracking_token
from app.modules.commerce.tracking import tracking_url

router = APIRouter(prefix="/storefront", tags=["commerce"])


async def get_store(db: AsyncSession, slug: str) -> Store:
    store = await db.scalar(select(Store).where(Store.slug == slug, Store.status == "active"))
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


def variant_label(variant: ProductVariant | None) -> str | None:
    if not variant:
        return None
    labels = [f"{link.option_value.option.name}: {link.option_value.name}" for link in variant.option_value_links if link.option_value and link.option_value.option]
    return ", ".join(labels) or None


def cart_response(cart: Cart) -> CartResponse:
    items = []
    for item in cart.items:
        image_url = next((media.url for media in item.product.media if media.status == "active" and media.media_type == "image"), None)
        items.append({"public_id": item.public_id, "product_public_id": item.product.public_id, "product_name": item.product.name, "product_slug": item.product.slug, "variant_public_id": item.variant.public_id if item.variant else None, "variant_label": variant_label(item.variant), "sku": (item.variant.sku or item.product.sku) if item.variant else item.product.sku, "image_url": image_url, "quantity": item.quantity, "unit_price_minor": item.unit_price_minor, "line_total_minor": item.unit_price_minor * item.quantity, "currency": cart.currency})
    return CartResponse(public_id=cart.public_id, currency=cart.currency, items=items, item_count=sum(item["quantity"] for item in items), subtotal_minor=sum(item["line_total_minor"] for item in items))


def order_response(order: Order, include_tracking: bool = False, store_slug: str | None = None, store_name: str | None = None) -> OrderResponse:
    return OrderResponse(
        public_id=order.public_id,
        order_number=order.order_number,
        status=OrderStatusResponse(public_id=order.status.public_id, code=order.status.code, name=order.status.name, description=order.status.description, sort_order=order.status.sort_order, is_terminal=order.status.is_terminal),
        store_name=store_name,
        customer_first_name=order.customer_first_name,
        customer_last_name=order.customer_last_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        notes=order.notes,
        currency=order.currency,
        subtotal_minor=order.subtotal_minor,
        total_minor=order.total_minor,
        items=[{"public_id": item.public_id, "product_public_id": item.product.public_id if item.product else "", "variant_public_id": item.variant.public_id if item.variant else None, "product_name": item.product_name, "variant_label": item.variant_label, "sku": item.sku, "quantity": item.quantity, "unit_price_minor": item.unit_price_minor, "line_total_minor": item.line_total_minor} for item in order.items],
        created_at=order.created_at.isoformat(),
        tracking_url=tracking_url(store_slug, make_tracking_token(order.public_id)) if include_tracking and store_slug else None,
        payment=payment_response(order.payment) if order.payment else None,
    )


def tracking_response(order: Order, store: Store) -> OrderTrackingResponse:
    return OrderTrackingResponse(
        store_name=store.name,
        order_number=order.order_number,
        status=OrderStatusResponse(public_id=order.status.public_id, code=order.status.code, name=order.status.name, description=order.status.description, sort_order=order.status.sort_order, is_terminal=order.status.is_terminal),
        status_history=[OrderStatusHistoryResponse(status=OrderStatusResponse(public_id=item.status.public_id, code=item.status.code, name=item.status.name, description=item.status.description, sort_order=item.status.sort_order, is_terminal=item.status.is_terminal), source=item.source, created_at=item.created_at.isoformat()) for item in order.status_history],
        customer_first_name=order.customer_first_name,
        currency=order.currency,
        subtotal_minor=order.subtotal_minor,
        total_minor=order.total_minor,
        items=[{"public_id": item.public_id, "product_public_id": item.product.public_id if item.product else "", "variant_public_id": item.variant.public_id if item.variant else None, "product_name": item.product_name, "variant_label": item.variant_label, "sku": item.sku, "quantity": item.quantity, "unit_price_minor": item.unit_price_minor, "line_total_minor": item.line_total_minor} for item in order.items],
        created_at=order.created_at.isoformat(),
        updated_at=order.updated_at.isoformat(),
        tracking_url=tracking_url(store.slug, make_tracking_token(order.public_id)),
        payment=payment_response(order.payment) if order.payment else None,
    )


def set_cart_cookie(response: Response, store: Store, token: str) -> None:
    response.set_cookie(key="dukame_cart", value=token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30, path=f"/api/v1/storefront/{store.slug}")


@router.get("/{store_slug}/cart", response_model=CartResponse)
async def get_cart(store_slug: str, response: Response, dukame_cart: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)) -> CartResponse:
    store = await get_store(db, store_slug)
    cart = await CommerceService(db).get_or_create_cart(store, dukame_cart)
    set_cart_cookie(response, store, cart.token)
    return cart_response(cart)


@router.get("/{store_slug}/payment-methods", response_model=list)
async def list_storefront_payment_methods(store_slug: str, db: AsyncSession = Depends(get_db)):
    store = await get_store(db, store_slug)
    return await PaymentService(db).list_storefront_methods(store)


@router.post("/{store_slug}/cart/items", response_model=CartResponse)
async def add_cart_item(store_slug: str, payload: CartItemAdd, response: Response, dukame_cart: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)) -> CartResponse:
    store = await get_store(db, store_slug)
    cart = await CommerceService(db).add_item(store, dukame_cart, payload)
    set_cart_cookie(response, store, cart.token)
    return cart_response(cart)


@router.patch("/{store_slug}/cart/items/{item_public_id}", response_model=CartResponse)
async def update_cart_item(store_slug: str, item_public_id: str, payload: CartItemUpdate, response: Response, dukame_cart: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)) -> CartResponse:
    store = await get_store(db, store_slug)
    cart = await CommerceService(db).update_item(store, dukame_cart, item_public_id, payload)
    set_cart_cookie(response, store, cart.token)
    return cart_response(cart)


@router.delete("/{store_slug}/cart/items/{item_public_id}", response_model=CartResponse)
async def delete_cart_item(store_slug: str, item_public_id: str, response: Response, dukame_cart: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)) -> CartResponse:
    store = await get_store(db, store_slug)
    cart = await CommerceService(db).remove_item(store, dukame_cart, item_public_id)
    set_cart_cookie(response, store, cart.token)
    return cart_response(cart)


@router.post("/{store_slug}/cart/checkout", response_model=OrderResponse)
async def checkout(store_slug: str, payload: CheckoutRequest, response: Response, dukame_cart: str | None = Cookie(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), db: AsyncSession = Depends(get_db)) -> OrderResponse:
    store = await get_store(db, store_slug)
    order = await CommerceService(db).checkout(store, dukame_cart, payload, idempotency_key=idempotency_key)
    response.delete_cookie("dukame_cart", path=f"/api/v1/storefront/{store.slug}")
    return order_response(order, include_tracking=True, store_slug=store.slug, store_name=store.name)


@router.get("/{store_slug}/order/track/{tracking_token_value}", response_model=OrderTrackingResponse)
async def track_order(store_slug: str, tracking_token_value: str, db: AsyncSession = Depends(get_db)) -> OrderTrackingResponse:
    store = await get_store(db, store_slug)
    order = await CommerceService(db).get_public_order(store, tracking_token_value)
    return tracking_response(order, store)


@router.post("/{store_slug}/order/lookup", response_model=OrderTrackingResponse)
async def lookup_order(store_slug: str, payload: OrderLookupRequest, db: AsyncSession = Depends(get_db)) -> OrderTrackingResponse:
    """Public lookup by order number + phone. Returns tracking payload so the client can open the live tracking page."""
    store = await get_store(db, store_slug)
    order = await CommerceService(db).lookup_public_order(store, payload.order_number, payload.phone)
    return tracking_response(order, store)


@router.post(
    "/{store_slug}/order/track/{tracking_token_value}/payment/retry",
    response_model=PaymentResponse,
)
async def retry_tracked_payment(
    store_slug: str,
    tracking_token_value: str,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Customer STK retry authorized by the order tracking token (no login)."""
    store = await get_store(db, store_slug)
    order = await CommerceService(db).get_public_order(store, tracking_token_value)
    payment = await PaymentService(db).retry_storefront_payment(order)
    return payment_response(payment)
