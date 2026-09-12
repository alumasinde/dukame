"""Phase 3 notification queue contract tests."""

from pathlib import Path


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
