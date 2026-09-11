from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.commerce.models.payment import Payment


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    instructions: Mapped[str | None] = mapped_column(Text)
    config_encrypted: Mapped[str | None] = mapped_column(Text)
    callback_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    payments: Mapped[list["Payment"]] = relationship(back_populates="payment_method")

    __table_args__ = (
        Index("uq_payment_methods_store_code", "store_id", "code", unique=True),
        Index("ix_payment_methods_store_enabled", "store_id", "is_enabled", "sort_order"),
    )
