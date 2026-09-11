from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.auth.models.identity import User
    from app.modules.commerce.models.order import Order
    from app.modules.commerce.models.order_status import OrderStatus


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_statuses.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="merchant")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    order: Mapped["Order"] = relationship()
    status: Mapped["OrderStatus"] = relationship()
    actor_user: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_order_status_history_order_created", "order_id", "created_at"),
    )
