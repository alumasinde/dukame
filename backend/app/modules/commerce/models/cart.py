from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.catalogue.models.store import Store
    from app.modules.commerce.models.cart_item import CartItem


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship()
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_carts_store_checked_out", "store_id", "checked_out_at"),
        Index("ix_carts_expires_at", "expires_at"),
    )
