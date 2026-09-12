from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.commerce.models.cart import Cart
from app.modules.commerce.models.order_delivery import OrderDelivery
from app.modules.subscriptions.services.subscription import expire_due_subscriptions


async def cleanup_expired_carts(db: AsyncSession) -> int:
    result = await db.execute(
        delete(Cart).where(
            Cart.checked_out_at.is_(None),
            Cart.expires_at <= datetime.now(UTC),
        )
    )
    await db.commit()
    return result.rowcount or 0


async def cleanup_expired_delivery_otps(db: AsyncSession) -> int:
    result = await db.execute(
        update(OrderDelivery)
        .where(
            OrderDelivery.otp_expires_at.is_not(None),
            OrderDelivery.otp_expires_at <= datetime.now(UTC),
            OrderDelivery.otp_hash.is_not(None),
            OrderDelivery.otp_verified_at.is_(None),
        )
        .values(otp_hash=None, otp_expires_at=None, otp_attempts=0)
    )
    await db.commit()
    return result.rowcount or 0


async def expire_subscriptions(db: AsyncSession) -> int:
    """Mark past-period subscriptions as cancelled or expired."""
    count = await expire_due_subscriptions(db)
    if count:
        await db.commit()
    return count


async def run_maintenance(db: AsyncSession) -> dict[str, int]:
    """Run all periodic maintenance tasks. Returns counts per task."""
    results: dict[str, int] = {}
    results["expired_carts"] = await cleanup_expired_carts(db)
    results["expired_delivery_otps"] = await cleanup_expired_delivery_otps(db)
    results["expired_subscriptions"] = await expire_subscriptions(db)
    return results
