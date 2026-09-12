"""Phase 3 notification queue contract tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.catalogue.schemas.store import StoreUpdate
from app.modules.commerce.notifications import (
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    normalize_phone,
    phone_digits,
    platform_sms_configured,
    platform_whatsapp_configured,
    status_message,
    whatsapp_template_params,
)


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_notification_queue_has_durable_lease_fields() -> None:
    model = read("app/modules/commerce/models/order_notification.py")
    migration = read("migrations/versions/0026_notification_leases.py")
    assert "worker_id" in model
    assert "lease_expires_at" in model
    assert "0026_notification_leases" in migration
    assert "ix_order_notifications_processing_lease" in migration


def test_notification_worker_reclaims_expired_processing_jobs() -> None:
    service = read("app/modules/commerce/notifications.py")
    assert 'OrderNotification.status == "processing"' in service
    assert "OrderNotification.lease_expires_at <= now" in service
    assert "skip_locked=True" in service


def test_notification_worker_cannot_complete_another_worker_lease() -> None:
    service = read("app/modules/commerce/notifications.py")
    assert "OrderNotification.worker_id == worker_id" in service
    assert 'OrderNotification.status == "processing"' in service


def test_notification_worker_entrypoint_exists() -> None:
    worker = read("app/workers/notification_worker.py")
    assert "process_notification_queue" in worker
    assert "SessionLocal" in worker
    assert "SIGTERM" in worker


def test_notification_retry_backoff_is_configurable() -> None:
    config = read("app/core/config.py")
    service = read("app/modules/commerce/notifications.py")
    assert "notification_max_attempts" in config
    assert "notification_lease_seconds" in config
    assert "notification_max_backoff_seconds" in config
    assert "settings.notification_max_backoff_seconds" in service


def test_multi_channel_notification_support() -> None:
    service = read("app/modules/commerce/notifications.py")
    model = read("app/modules/commerce/models/order_notification.py")
    migration = read("migrations/versions/0030_store_notification_channels.py")
    assert "queue_order_notifications" in service
    assert "send_whatsapp" in read("app/modules/commerce/notification_channels.py")
    assert "dispatch_notification" in read("app/modules/commerce/notification_channels.py")
    assert 'CHANNEL_WHATSAPP = "whatsapp"' in service
    assert "template_name" in model
    assert "template_params" in model
    assert "sms_notifications_enabled" in migration
    assert "whatsapp_notifications_enabled" in migration
    assert "whatsapp_opt_in_at" in migration


def test_whatsapp_supports_meta_and_bsp_providers() -> None:
    channels = read("app/modules/commerce/notification_channels.py")
    config = read("app/core/config.py")
    assert '"meta"' in channels
    assert '"bsp"' in channels
    assert "whatsapp_provider" in config
    assert "whatsapp_phone_number_id" in config
    assert "whatsapp_api_url" in config
    assert "whatsapp_status_template" in config


def test_store_exposes_notification_toggles() -> None:
    model = read("app/modules/catalogue/models/store.py")
    schema = read("app/modules/catalogue/schemas/store.py")
    assert "sms_notifications_enabled" in model
    assert "whatsapp_notifications_enabled" in model
    assert "sms_notifications_enabled" in schema
    assert "whatsapp_notifications_enabled" in schema


def test_store_update_allows_notification_toggles() -> None:
    payload = StoreUpdate(sms_notifications_enabled=True, whatsapp_notifications_enabled=False)
    data = payload.model_dump(exclude_unset=True)
    assert data["sms_notifications_enabled"] is True
    assert data["whatsapp_notifications_enabled"] is False


def test_store_update_rejects_null_notification_toggles() -> None:
    with pytest.raises(ValidationError):
        StoreUpdate(sms_notifications_enabled=None)


def test_normalize_phone_kenyan_formats() -> None:
    assert normalize_phone("0712345678") == "+254712345678"
    assert normalize_phone("254712345678") == "+254712345678"
    assert normalize_phone("+254712345678") == "+254712345678"
    assert phone_digits("0712345678") == "254712345678"


def test_whatsapp_template_params_order() -> None:
    class _Order:
        order_number = "A100"

    class _Status:
        name = "Confirmed"

    params = whatsapp_template_params("Demo", _Order(), _Status(), "https://example.com/t")  # type: ignore[arg-type]
    assert params == ["Demo", "A100", "Confirmed", "https://example.com/t"]
    assert "Track your order" in status_message("Demo", _Order(), _Status(), "https://example.com/t")  # type: ignore[arg-type]


def test_commerce_uses_unified_notification_queue() -> None:
    service = read("app/modules/commerce/service.py")
    payment = read("app/modules/commerce/payment_service.py")
    assert "queue_order_notifications" in service
    assert "queue_order_notifications" in payment
