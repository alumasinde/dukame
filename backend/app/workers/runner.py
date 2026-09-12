import asyncio
import logging
import time

import app.models 
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.core.redis import redis_client
from app.modules.commerce.notifications import process_notification_queue
from app.workers.maintenance import run_maintenance

logger = logging.getLogger(__name__)


async def run() -> None:
    configure_logging(settings.log_level)
    await redis_client.ping()
    logger.info("worker_ready")

    last_maintenance_at = 0.0
    maintenance_interval = float(settings.maintenance_interval_seconds)

    try:
        while True:
            # --- notification processing (high frequency) ---
            try:
                async with SessionLocal() as db:
                    processed = await process_notification_queue(db)
                if processed:
                    logger.info("notifications_processed", extra={"count": processed})
            except Exception:
                logger.exception("notification_worker_iteration_failed")

            # --- periodic maintenance (lower frequency) ---
            now = time.monotonic()
            if now - last_maintenance_at >= maintenance_interval:
                try:
                    async with SessionLocal() as db:
                        results = await run_maintenance(db)
                    if any(results.values()):
                        logger.info("maintenance_completed", extra=results)
                    last_maintenance_at = now
                except Exception:
                    logger.exception("maintenance_worker_iteration_failed")
                    # Still advance the clock so a persistent failure does not
                    # spin the loop at full speed.
                    last_maintenance_at = now

            await asyncio.sleep(settings.notification_poll_seconds)
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(run())
