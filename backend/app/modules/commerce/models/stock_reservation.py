"""
Stock reservation model to hold inventory during pending payment.

Reservation flow:
1. Checkout initiates → reserve stock with expiry
2. Payment succeeds → finalize reservation (move to sale)
3. Payment fails/expires/cancelled → release reservation

Available stock = on_hand_quantity - active_reservations
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.catalogue.models.product import Product
    from app.modules.catalogue.models.store import Store
    from app.modules.catalogue.models.variant import ProductVariant
    from app.modules.commerce.models.order import Order


class StockReservation(Base):
    """
    Holds reserved inventory while payment is pending.
    
    States:
    - pending: awaiting payment confirmation
    - finalized: payment confirmed, converted to sale
    - released: payment failed/expired/cancelled
    """
    __tablename__ = "stock_reservations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("product_variants.id", ondelete="CASCADE"))
    
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending, finalized, released
    
    # Reservation window: typically 10-15 minutes for payment
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_reason: Mapped[str | None] = mapped_column(String(100))  # payment_failed, payment_expired, user_cancelled
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship()
    order: Mapped["Order | None"] = relationship()
    product: Mapped["Product"] = relationship()
    variant: Mapped["ProductVariant | None"] = relationship()

    __table_args__ = (
        Index("ix_stock_reservations_store_status", "store_id", "status"),
        Index("ix_stock_reservations_order", "order_id"),
        Index("ix_stock_reservations_product_variant", "product_id", "variant_id"),
        Index("ix_stock_reservations_expires", "expires_at"),
    )
