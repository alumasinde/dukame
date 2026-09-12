from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.tenancy.models.tenant import Tenant


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    monthly_price_minor: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    quarterly_price_minor: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    yearly_price_minor: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="KES")
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    badge: Mapped[str | None] = mapped_column(String(64))
    highlight: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    features: Mapped[list["PlanFeature"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")

    def price_for_interval(self, interval: str) -> int:
        mapping = {
            "monthly": self.monthly_price_minor,
            "quarterly": self.quarterly_price_minor,
            "yearly": self.yearly_price_minor,
        }
        if interval not in mapping:
            raise ValueError(f"Unsupported billing interval: {interval}")
        return mapping[interval]

    @property
    def is_free(self) -> bool:
        return (
            self.monthly_price_minor <= 0
            and self.quarterly_price_minor <= 0
            and self.yearly_price_minor <= 0
        )


class PlanFeature(Base):
    __tablename__ = "plan_features"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    plan: Mapped[Plan] = relationship(back_populates="features")

    __table_args__ = (
        UniqueConstraint("plan_id", "feature_key", name="uq_plan_features_plan_key"),
        Index("ix_plan_features_key", "feature_key"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    billing_interval: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="monthly"
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0"
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship()
    plan: Mapped[Plan] = relationship(back_populates="subscriptions")
    events: Mapped[list["SubscriptionEvent"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_subscriptions_tenant"),
        Index("ix_subscriptions_status_period", "status", "current_period_end"),
    )


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Any | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    subscription: Mapped[Subscription] = relationship(back_populates="events")

    __table_args__ = (
        Index(
            "ix_subscription_events_subscription_created",
            "subscription_id",
            "created_at",
        ),
    )
