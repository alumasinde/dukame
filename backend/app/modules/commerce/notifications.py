from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_notification import OrderNotification
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.tracking import tracking_token, tracking_url

logger = logging.getLogger(__name__)


def normalize_phone(value: str) -> str:
    phone = "".join(character for character in value.strip() if character.isdigit() or character == "+")
    if phone.startswith(("07", "01")):
        return "+254" + phone[1:]
    if phone.startswith("254"):
        return "+" + phone
    return phone


def status_message(store_name: str, order: Order, status: OrderStatus, url: str) -> str:
    return f"{store_name}: Order #{order.order_number} is now {status.name}. Track your order: {url}"


async def queue_order_sms(db: AsyncSession, order: Order, status: OrderStatus, store_name: str, store_slug: str) -> None:
    if settings.sms_provider == "none":
        return
    recipient = normalize_phone(order.customer_phone)
    if not recipient:
        return
    url = tracking_url(store_slug, tracking_token(order.public_id))
    exists = await db.scalar(
        select(OrderNotification.id).where(
            OrderNotification.order_id == order.id,
            OrderNotification.status_id == status.id,
            OrderNotification.channel == "sms",
        )
    )
    if exists is not None:
        return
    db.add(
        OrderNotification(
            order_id=order.id,
            status_id=status.id,
            channel="sms",
            recipient=recipient,
            message=status_message(store_name, order, status, url),
            tracking_url=url,
        )
    )


async def send_sms(notification: OrderNotification) -> str | None:
    if settings.sms_provider != "africastalking":
        raise RuntimeError(f"Unsupported SMS provider: {settings.sms_provider}")
    if settings.sms_api_key is None or not settings.sms_api_key.get_secret_value() or not settings.sms_username:
        raise RuntimeError("Africa's Talking SMS credentials are not configured")
    data: dict[str, str] = {"username": settings.sms_username, "to": notification.recipient, "message": notification.message}
    if settings.sms_sender_id:
        data["from"] = settings.sms_sender_id
    headers = {"apiKey": settings.sms_api_key.get_secret_value(), "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(settings.sms_api_url, data=data, headers=headers)
        response.raise_for_status()
        payload = response.json()
    recipients = payload.get("SMSMessageData", {}).get("Recipients", [])
    if not recipients:
        raise RuntimeError("SMS provider returned no recipient result")
    result = recipients[0]
    status_code = str(result.get("statusCode", ""))
    if status_code not in {"100", "101", "102"}:
        raise RuntimeError(f"SMS provider rejected notification with status {status_code}")
    return str(result.get("messageId")) if result.get("messageId") else None


async def process_notification_queue(db: AsyncSession, limit: int = 10, worker_id: str | None = None) -> int:
    if settings.sms_provider == "none":
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
            message_id = await send_sms(notification)
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
            next_available = now + timedelta(seconds=min(settings.notification_max_backoff_seconds, 2 ** notification.attempts * 5))
            await db.execute(
                OrderNotification.__table__.update()
                .where(
                    OrderNotification.id == notification.id,
                    OrderNotification.worker_id == worker_id,
                    OrderNotification.status == "processing",
                )
                .values(
                    status=next_status,
                    available_at=next_available,
                    last_error=str(exc)[:1000],
                    lease_expires_at=None,
                    worker_id=None,
                )
            )
            await db.commit()
            logger.exception("order_notification_failed", extra={"notification_id": notification.id})
    return processed
