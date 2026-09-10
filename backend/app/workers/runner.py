import asyncio
import logging

from app.core.logging import configure_logging
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


async def run() -> None:
    configure_logging("INFO")
    await redis_client.ping()
    logger.info("worker_ready")
    try:
        await asyncio.Event().wait()
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(run())
