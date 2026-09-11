from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    payment_method_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payment_methods.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128))
    provider_status_code: Mapped[str | None] = mapped_column(String(64))
    failure_reason: Mapped[str | None] = mapped_column(String(1000))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    order = relationship("Order", back_populates="payment")
    payment_method = relationship("PaymentMethod", back_populates="payments")
    attempts = relationship("PaymentAttempt", back_populates="payment", cascade="all, delete-orphan", order_by="PaymentAttempt.created_at")
    events = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan", order_by="PaymentEvent.created_at")

    __table_args__ = (
        Index("ix_payments_store_status_created", "store_id", "status", "created_at"),
        Index("ix_payments_provider_reference", "provider_reference"),
    )
