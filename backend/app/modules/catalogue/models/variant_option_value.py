from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.catalogue.models.option_value import ProductOptionValue
    from app.modules.catalogue.models.variant import ProductVariant


class ProductVariantOptionValue(Base):
    __tablename__ = "product_variant_option_values"

    variant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True)
    option_value_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_option_values.id", ondelete="CASCADE"), primary_key=True)

    variant: Mapped["ProductVariant"] = relationship(back_populates="option_value_links")
    option_value: Mapped["ProductOptionValue"] = relationship(back_populates="variant_links")

    __table_args__ = (Index("ix_variant_option_values_option_value", "option_value_id"),)
