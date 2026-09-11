from __future__ import annotations

import hashlib
import hmac

from app.core.config import settings


def tracking_token(public_id: str) -> str:
    signature = hmac.new(
        settings.jwt_secret.get_secret_value().encode("utf-8"),
        public_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{public_id}.{signature}"


def tracking_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_tracking_token(public_id: str, token: str) -> bool:
    expected = tracking_token(public_id)
    return hmac.compare_digest(expected, token)


def tracking_url(store_slug: str, token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/{store_slug}/order/track/{token}"
