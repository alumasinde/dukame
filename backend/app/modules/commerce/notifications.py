from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.commerce.models.order import Order
from app.modules.commerce.models.order_notification import OrderNotification
from app.modules.commerce.models.order_status import OrderStatus
from app.modules.commerce.tracking import tracking_token, tracking_url

logger = logging.getLogger(__name__)


def normalize_phone(value: str) -> str:
    phone = "".join(character for character in value.strip() if character.isdigit() or character == "+")
    if phone.startswith("07") or phone.startswith("01"):
        return "+254" + phone[1:]
    if phone.startswith("254"):
        return "+" + phone
    return phone


def status_message(order: Order, status: OrderStatus, url: str) -> str:
    return (
        f"{order.store.name}: Order #{order.order_number} is now {status.name}. "
        f"Track your order: {url}"
    )


async def queue_order_sms(
    db: AsyncSession,
    order: Order,
    status: OrderStatus,
    store_slug: str,
) -> None:
    if settings.sms_provider == "none":
        return
    recipient = normalize_phone(order.customer_phone)
    if not recipient:
        return
    token = tracking_token(order.public_id)
    url = tracking_url(store_slug, token)
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
            message=status_message(order, status, url),
            tracking_url=url,
        )
    )


async def send_sms(notification: OrderNotification) -> str | None:
    if settings.sms_provider != "africastalking":
        raise RuntimeError(f"Unsupported SMS provider: {settings.sms_provider}")
    if settings.sms_api_key is None or not settings.sms_username:
        raise RuntimeError("Africa's Talking SMS credentials are not configured")

    data = {
        "username": settings.sms_username,
        "to": notification.recipient,
        "message": notification.message,
    }
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


async def process_notification_queue(db: AsyncSession, limit: int = 10) -> int:
    if settings.sms_provider == "none":
        return 0
    now = datetime.now(UTC)
    notifications = list(
        (
            await db.scalars(
                select(OrderNotification)
                .where(
                    OrderNotification.status == "pending",
                    OrderNotification.available_at <= now,
                    OrderNotification.attempts < settings.notification_max_attempts,
                )
                .order_by(OrderNotification.created_at.asc(), OrderNotification.id.asc())
                .limit(limit)
                .with_for_update()
            )
        ).all()
    )
    if not notifications:
        return 0

    for notification in notifications:
        notification.status = "processing"
        notification.attempts += 1
    await db.commit()

    processed = 0
    for notification in notifications:
        try:
            message_id = await send_sms(notification)
            notification.status = "sent"
            notification.sent_at = datetime.now(UTC)
            notification.provider_message_id = message_id
            notification.last_error = None
            processed += 1
        except Exception as exc:
            notification.status = "pending" if notification.attempts < settings.notification_max_attempts else "failed"
            notification.available_at = datetime.now(UTC) + timedelta(seconds=min(300, 2 ** notification.attempts * 5))
            notification.last_error = str(exc)[:1000]
            logger.exception("order_notification_failed", extra={"notification_id": notification.id})
        await db.commit()
    return processed
