from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commerce.models.audit_log import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    tenant_id: int,
    action: str,
    entity_type: str,
    entity_public_id: str,
    store_id: int | None = None,
    actor_user_id: int | None = None,
    request_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        store_id=store_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_public_id=entity_public_id,
        request_id=request_id,
        before=before,
        after=after,
        metadata_json=metadata,
    )
    db.add(entry)
    return entry
