import json
import hashlib
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.commerce.models.idempotency_key import IdempotencyKey

class IdempotencyEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def calculate_hash(payload: object) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def validate_key(key: str | None) -> str | None:
        if key is None:
            return None
        value = key.strip()
        if not value or len(value) > 128:
            raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")
        return value

    async def find_key(self, store_id: int, operation: str, scope_key: str, key: str) -> IdempotencyKey | None:
        return await self.db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.store_id == store_id,
                IdempotencyKey.operation == operation,
                IdempotencyKey.scope_key == scope_key,
                IdempotencyKey.key == key
            )
        )

    async def claim_key(self, store_id: int, operation: str, scope_key: str, key: str, request_hash: str) -> IdempotencyKey | None:
        existing = await self.find_key(store_id, operation, scope_key, key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used with a different request")
            return existing
        return None
