import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.core.redis import redis_client
from app.modules.commerce.notifications import process_notification_queue

logger = logging.getLogger(__name__)


async def run() -> None:
    configure_logging(settings.log_level)
    await redis_client.ping()
    logger.info("worker_ready")
    try:
        while True:
            try:
                async with SessionLocal() as db:
                    processed = await process_notification_queue(db)
                if processed:
                    logger.info("notifications_processed", extra={"count": processed})
            except Exception:
                logger.exception("notification_worker_iteration_failed")
            await asyncio.sleep(settings.notification_poll_seconds)
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(run())
