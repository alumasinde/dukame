from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    payment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    event_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payment = relationship("Payment", back_populates="events")

    __table_args__ = (Index("ix_payment_events_payment_created", "payment_id", "created_at"),)
