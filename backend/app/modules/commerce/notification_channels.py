from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.modules.commerce.models.order_notification import OrderNotification


def phone_digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


async def send_sms(notification: OrderNotification) -> str | None:
    if settings.sms_provider == "none":
        raise RuntimeError("SMS provider is disabled")
    if settings.sms_provider != "africastalking":
        raise RuntimeError(f"Unsupported SMS provider: {settings.sms_provider}")
    if settings.sms_api_key is None or not settings.sms_api_key.get_secret_value() or not settings.sms_username:
        raise RuntimeError("Africa's Talking SMS credentials are not configured")
    data: dict[str, str] = {
        "username": settings.sms_username,
        "to": notification.recipient,
        "message": notification.message,
    }
    if settings.sms_sender_id:
        data["from"] = settings.sms_sender_id
    headers = {"apiKey": settings.sms_api_key.get_secret_value(), "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
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


def _whatsapp_auth_headers() -> dict[str, str]:
    if settings.whatsapp_api_token is None or not settings.whatsapp_api_token.get_secret_value():
        raise RuntimeError("WhatsApp API token is not configured")
    return {
        "Authorization": f"Bearer {settings.whatsapp_api_token.get_secret_value()}",
        "Content-Type": "application/json",
    }


def _build_whatsapp_template_payload(notification: OrderNotification) -> dict[str, Any]:
    to = phone_digits(notification.recipient)
    template_name = notification.template_name or settings.whatsapp_status_template
    language = settings.whatsapp_template_language
    body_params = []
    if isinstance(notification.template_params, dict):
        raw = notification.template_params.get("body") or []
        body_params = [{"type": "text", "text": str(item)} for item in raw]
    components: list[dict[str, Any]] = []
    if body_params:
        components.append({"type": "body", "parameters": body_params})
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components,
        },
    }


async def send_whatsapp(notification: OrderNotification) -> str | None:
    provider = settings.whatsapp_provider
    if provider == "none":
        raise RuntimeError("WhatsApp provider is disabled")
    if provider not in {"meta", "bsp"}:
        raise RuntimeError(f"Unsupported WhatsApp provider: {provider}")
    payload = _build_whatsapp_template_payload(notification)
    headers = _whatsapp_auth_headers()
    if provider == "meta":
        if not settings.whatsapp_phone_number_id:
            raise RuntimeError("WhatsApp phone_number_id is required for Meta Cloud API")
        url = f"{settings.whatsapp_api_base_url.rstrip('/')}/{settings.whatsapp_phone_number_id}/messages"
    else:
        url = settings.whatsapp_api_url
        if not url:
            raise RuntimeError("WhatsApp BSP API URL is not configured")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    messages = body.get("messages") or []
    if messages and isinstance(messages, list):
        message_id = messages[0].get("id")
        if message_id:
            return str(message_id)
    for key in ("message_id", "id", "provider_message_id"):
        if body.get(key):
            return str(body[key])
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    if data.get("message_id"):
        return str(data["message_id"])
    return None


async def dispatch_notification(notification: OrderNotification) -> str | None:
    if notification.channel == "sms":
        return await send_sms(notification)
    if notification.channel == "whatsapp":
        return await send_whatsapp(notification)
    raise RuntimeError(f"Unsupported notification channel: {notification.channel}")
