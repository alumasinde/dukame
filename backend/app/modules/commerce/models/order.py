from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.catalogue.models.store import Store
    from app.modules.commerce.models.order_item import OrderItem
    from app.modules.commerce.models.order_notification import OrderNotification
    from app.modules.commerce.models.order_status import OrderStatus
    from app.modules.commerce.models.order_status_history import OrderStatusHistory
    from app.modules.commerce.models.payment import Payment
    from app.modules.customers.models.customer import Customer


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customers.id", ondelete="SET NULL"))
    status_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_statuses.id", ondelete="RESTRICT"), nullable=False)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    tracking_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    customer_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(320))
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    store: Mapped["Store"] = relationship()
    customer: Mapped["Customer | None"] = relationship(back_populates="orders")
    status: Mapped["OrderStatus"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )
    notifications: Mapped[list["OrderNotification"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_orders_store_status_created", "store_id", "status_id", "created_at"),
        Index("ix_orders_store_customer", "store_id", "customer_id"),
        Index("ix_orders_store_customer_phone", "store_id", "customer_phone"),
    )
