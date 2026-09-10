import time

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import redis_client


class RateLimitExceeded(Exception):
    pass


async def check_rate_limit(
    key: str,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> None:
    if not settings.rate_limit_enabled:
        return

    configured_limit = (
        limit if limit is not None else settings.rate_limit_requests
    )
    configured_window = (
        window_seconds
        if window_seconds is not None
        else settings.rate_limit_window_seconds
    )
    bucket = f"rl:{key}:{int(time.time() // configured_window)}"

    try:
        count = await redis_client.incr(bucket)
        if count == 1:
            await redis_client.expire(bucket, configured_window + 1)
    except RedisError as exc:
        raise RuntimeError("Rate-limit infrastructure unavailable") from exc

    if count > configured_limit:
        raise RateLimitExceeded
