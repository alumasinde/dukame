from __future__ import annotations

import hashlib
import json
import secrets

from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.core.config import settings


def _fernet() -> Fernet:
    if settings.payment_encryption_key is None or not settings.payment_encryption_key.get_secret_value():
        raise HTTPException(status_code=503, detail="Payment encryption is not configured")
    try:
        return Fernet(settings.payment_encryption_key.get_secret_value().encode())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Payment encryption is not configured correctly") from exc


def encrypt_config(config: dict[str, str]) -> str:
    payload = json.dumps(config, separators=(",", ":"), sort_keys=True).encode()
    return _fernet().encrypt(payload).decode()


def decrypt_config(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    try:
        payload = _fernet().decrypt(value.encode())
        data = json.loads(payload.decode())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Payment configuration could not be decrypted") from exc
    if not isinstance(data, dict) or not all(isinstance(key, str) and isinstance(item, str) for key, item in data.items()):
        raise HTTPException(status_code=503, detail="Payment configuration is invalid")
    return data


def new_callback_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def callback_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
