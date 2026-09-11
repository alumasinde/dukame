from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.catalogue.models.product import Product
    from app.modules.catalogue.models.variant_option_value import ProductVariantOptionValue


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100))
    price_minor: Mapped[int | None] = mapped_column(Integer)
    compare_at_price_minor: Mapped[int | None] = mapped_column(Integer)
    inventory_tracking: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    inventory_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    product: Mapped["Product"] = relationship(back_populates="variants")
    option_value_links: Mapped[list["ProductVariantOptionValue"]] = relationship(back_populates="variant", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_product_variants_store_sku"),
        Index("ix_product_variants_product_status", "product_id", "status"),
        Index("ix_product_variants_store", "store_id"),
    )
