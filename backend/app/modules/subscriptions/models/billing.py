from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SubscriptionInvoice(Base):
    __tablename__ = "subscription_invoices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)  # upgrade|renewal|reactivation
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    metadata_json: Mapped[Any | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    payments: Mapped[list["SubscriptionPayment"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_subscription_invoices_tenant_status", "tenant_id", "status", "created_at"),
        Index("ix_subscription_invoices_subscription_status", "subscription_id", "status"),
    )


class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscription_invoices.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, server_default="mpesa")
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    provider_checkout_request_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    provider_merchant_request_id: Mapped[str | None] = mapped_column(String(128))
    provider_reference: Mapped[str | None] = mapped_column(String(128))
    provider_status_code: Mapped[str | None] = mapped_column(String(64))
    failure_reason: Mapped[str | None] = mapped_column(String(1000))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice: Mapped[SubscriptionInvoice] = relationship(back_populates="payments")

    __table_args__ = (
        Index("ix_subscription_payments_invoice_status", "invoice_id", "status"),
    )


class UsageMeter(Base):
    __tablename__ = "usage_meters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "feature_key", "period_key", name="uq_usage_meters_tenant_feature_period"
        ),
        Index("ix_usage_meters_tenant_feature", "tenant_id", "feature_key"),
    )
