from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.catalogue.models.option import ProductOption
    from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue


class ProductOptionValue(Base):
    __tablename__ = "product_option_values"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    option_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_options.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    option: Mapped["ProductOption"] = relationship(back_populates="values")
    variant_links: Mapped[list["ProductVariantOptionValue"]] = relationship(back_populates="option_value")

    __table_args__ = (
        UniqueConstraint("option_id", "slug", name="uq_product_option_values_option_slug"),
        Index("ix_product_option_values_option_status", "option_id", "status"),
    )
