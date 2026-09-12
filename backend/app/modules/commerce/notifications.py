from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.catalogue.models.store import Store
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_notification import OrderNotification
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.notification_channels import dispatch_notification, phone_digits
from app.modules.commerce.tracking import tracking_token, tracking_url
from app.modules.customers.models.customer import Customer

logger = logging.getLogger(__name__)

CHANNEL_SMS = "sms"
CHANNEL_WHATSAPP = "whatsapp"


def normalize_phone(value: str) -> str:
    """Normalize Kenyan numbers to +2547XXXXXXXX form."""
    phone = "".join(character for character in value.strip() if character.isdigit() or character == "+")
    if phone.startswith(("07", "01")):
        return "+254" + phone[1:]
    if phone.startswith("254"):
        return "+" + phone
    if phone.startswith("+"):
        return phone
    return phone


def status_message(store_name: str, order: Order, status: OrderStatus, url: str) -> str:
    return f"{store_name}: Order #{order.order_number} is now {status.name}. Track your order: {url}"


def whatsapp_template_params(store_name: str, order: Order, status: OrderStatus, url: str) -> list[str]:
    """Ordered body parameters for the status-update utility template."""
    return [store_name, str(order.order_number), status.name, url]


def platform_sms_configured() -> bool:
    return settings.sms_provider != "none"


def platform_whatsapp_configured() -> bool:
    return settings.whatsapp_provider != "none"


async def _notification_exists(db: AsyncSession, order_id: int, status_id: int, channel: str) -> bool:
    exists = await db.scalar(
        select(OrderNotification.id).where(
            OrderNotification.order_id == order_id,
            OrderNotification.status_id == status_id,
            OrderNotification.channel == channel,
        )
    )
    return exists is not None


async def _should_queue_whatsapp(db: AsyncSession, order: Order, store: Store, customer: Customer | None) -> bool:
    if not platform_whatsapp_configured() or not store.whatsapp_notifications_enabled:
        return False
    if not settings.whatsapp_require_opt_in:
        return True
    if customer is not None:
        return customer.whatsapp_opt_in_at is not None
    if order.customer_id is None:
        return False
    loaded = await db.scalar(select(Customer).where(Customer.id == order.customer_id))
    return loaded is not None and loaded.whatsapp_opt_in_at is not None


async def queue_order_notifications(
    db: AsyncSession,
    order: Order,
    status: OrderStatus,
    store: Store,
    *,
    customer: Customer | None = None,
) -> None:
    """Queue SMS and/or WhatsApp notifications based on platform + store settings."""
    if not order.customer_phone:
        return
    recipient = normalize_phone(order.customer_phone)
    if not recipient or len(phone_digits(recipient)) < 10:
        return

    url = tracking_url(store.slug, tracking_token(order.public_id))
    message = status_message(store.name, order, status, url)

    if platform_sms_configured() and store.sms_notifications_enabled:
        if not await _notification_exists(db, order.id, status.id, CHANNEL_SMS):
            db.add(
                OrderNotification(
                    order_id=order.id,
                    status_id=status.id,
                    store_id=store.id,
                    channel=CHANNEL_SMS,
                    recipient=recipient,
                    message=message,
                    tracking_url=url,
                )
            )

    if await _should_queue_whatsapp(db, order, store, customer):
        if not await _notification_exists(db, order.id, status.id, CHANNEL_WHATSAPP):
            params = whatsapp_template_params(store.name, order, status, url)
            db.add(
                OrderNotification(
                    order_id=order.id,
                    status_id=status.id,
                    store_id=store.id,
                    channel=CHANNEL_WHATSAPP,
                    recipient=recipient,
                    message=message,
                    tracking_url=url,
                    template_name=settings.whatsapp_status_template,
                    template_params={"body": params},
                )
            )


async def queue_order_sms(
    db: AsyncSession,
    order: Order,
    status: OrderStatus,
    store_name: str,
    store_slug: str,
) -> None:
    """Backward-compatible wrapper; prefers full store-aware queue when store is resolvable."""
    store = await db.scalar(select(Store).where(Store.slug == store_slug))
    if store is not None:
        await queue_order_notifications(db, order, status, store)
        return
    if not platform_sms_configured():
        return
    recipient = normalize_phone(order.customer_phone or "")
    if not recipient:
        return
    url = tracking_url(store_slug, tracking_token(order.public_id))
    if await _notification_exists(db, order.id, status.id, CHANNEL_SMS):
        return
    db.add(
        OrderNotification(
            order_id=order.id,
            status_id=status.id,
            channel=CHANNEL_SMS,
            recipient=recipient,
            message=status_message(store_name, order, status, url),
            tracking_url=url,
        )
    )


def _any_channel_enabled() -> bool:
    return platform_sms_configured() or platform_whatsapp_configured()


async def process_notification_queue(db: AsyncSession, limit: int = 10, worker_id: str | None = None) -> int:
    if not _any_channel_enabled():
        return 0
    if limit < 1:
        raise ValueError("limit must be positive")
    worker_id = worker_id or secrets.token_hex(16)
    now = datetime.now(UTC)
    lease_expires_at = now + timedelta(seconds=settings.notification_lease_seconds)
    eligible = or_(
        (OrderNotification.status == "pending") & (OrderNotification.available_at <= now),
        (OrderNotification.status == "processing") & (OrderNotification.lease_expires_at <= now),
    )
    notifications = list(
        (
            await db.scalars(
                select(OrderNotification)
                .where(
                    eligible,
                    OrderNotification.attempts < settings.notification_max_attempts,
                )
                .order_by(OrderNotification.created_at.asc(), OrderNotification.id.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    if not notifications:
        return 0
    for notification in notifications:
        notification.status = "processing"
        notification.attempts += 1
        notification.worker_id = worker_id
        notification.lease_expires_at = lease_expires_at
    await db.commit()

    processed = 0
    for notification in notifications:
        try:
            message_id = await dispatch_notification(notification)
            now = datetime.now(UTC)
            await db.execute(
                OrderNotification.__table__.update()
                .where(
                    OrderNotification.id == notification.id,
                    OrderNotification.worker_id == worker_id,
                    OrderNotification.status == "processing",
                )
                .values(
                    status="sent",
                    sent_at=now,
                    provider_message_id=message_id,
                    last_error=None,
                    lease_expires_at=None,
                    worker_id=None,
                )
            )
            await db.commit()
            processed += 1
        except Exception as exc:
            now = datetime.now(UTC)
            next_status = "pending" if notification.attempts < settings.notification_max_attempts else "failed"
            backoff = min(
                settings.notification_max_backoff_seconds,
                2 ** max(notification.attempts - 1, 0),
            )
            available_at = now + timedelta(seconds=backoff) if next_status == "pending" else now
            await db.execute(
                OrderNotification.__table__.update()
                .where(
                    OrderNotification.id == notification.id,
                    OrderNotification.worker_id == worker_id,
                    OrderNotification.status == "processing",
                )
                .values(
                    status=next_status,
                    last_error=str(exc)[:2000],
                    available_at=available_at,
                    lease_expires_at=None,
                    worker_id=None,
                )
            )
            await db.commit()
            logger.warning(
                "notification_send_failed",
                extra={
                    "notification_id": notification.id,
                    "channel": notification.channel,
                    "attempts": notification.attempts,
                    "error": str(exc),
                },
            )
    return processed
