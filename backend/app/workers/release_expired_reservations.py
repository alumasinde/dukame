"""
Maintenance worker to release expired stock reservations.
Runs periodically to clean up pending reservations that exceed TTL.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commerce.models.stock_reservation import StockReservation


async def release_expired_reservations(db: AsyncSession) -> int:
    """
    Release all expired stock reservations.
    
    Returns:
        Number of reservations released
    """
    now = datetime.now(UTC)
    
    # Find all expired pending reservations
    expired = list((await db.scalars(
        select(StockReservation).where(
            StockReservation.status == "pending",
            StockReservation.expires_at <= now
        )
    )).all())
    
    count = 0
    for reservation in expired:
        reservation.status = "released"
        reservation.released_at = now
        reservation.release_reason = "payment_window_expired"
        count += 1
    
    if count > 0:
        await db.commit()
    
    return count
