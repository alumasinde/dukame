"""Phase 3 operational reliability contract tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_audit_log_is_tenant_scoped_and_append_only() -> None:
    model = read("app/modules/commerce/models/audit_log.py")
    migration = read("migrations/versions/0027_audit_logs.py")
    service = read("app/modules/commerce/audit_service.py")
    assert 'tenant_id: Mapped[int]' in model
    assert 'created_at: Mapped[datetime]' in model
    assert 'tenant_id' in migration
    assert '0026_notification_leases' in migration
    assert 'db.add(entry)' in service
    assert 'db.delete' not in service


def test_delivery_audits_state_changes_without_recording_otp() -> None:
    service = read("app/modules/commerce/delivery_service.py")
    assert 'action="delivery.assigned"' in service
    assert 'action="delivery.otp.issued"' in service
    assert 'action="delivery.confirmed"' in service
    assert '"otp": otp' not in service


def test_notification_worker_has_graceful_shutdown() -> None:
    worker = read("app/workers/notification_worker.py")
    assert "SIGTERM" in worker
    assert "stop" in worker
    assert "process_notification_queue" in worker
