import secrets
from datetime import datetime, timedelta
from hashlib import sha256

from app.core.time import utc_now


def random_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def expires_in(hours: int) -> datetime:
    return utc_now() + timedelta(hours=hours)
