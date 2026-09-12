from __future__ import annotations

import asyncio
import logging
import signal

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.commerce.notifications import process_notification_queue

logger = logging.getLogger(__name__)


async def run() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    for signum in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(signum, stop.set)
        except NotImplementedError:
            pass

    while not stop.is_set():
        try:
            async with SessionLocal() as db:
                processed = await process_notification_queue(db, worker_id=settings.notification_worker_id)
            if processed == 0:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=settings.notification_poll_seconds)
                except TimeoutError:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("notification_worker_cycle_failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=settings.notification_poll_seconds)
            except TimeoutError:
                pass


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level)
    asyncio.run(run())
