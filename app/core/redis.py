from redis.asyncio import Redis

from app.core.config import settings

redis_client = Redis.from_url(str(settings.redis_url), decode_responses=True)
