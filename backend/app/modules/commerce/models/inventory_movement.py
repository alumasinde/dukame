from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.auth.models.identity import User
    from app.modules.catalogue.models.product import Product
    from app.modules.catalogue.models.store import Store
    from app.modules.catalogue.models.variant import ProductVariant


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    store_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("product_variants.id", ondelete="RESTRICT"))
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(500))
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    store: Mapped["Store"] = relationship()
    product: Mapped["Product"] = relationship()
    variant: Mapped["ProductVariant | None"] = relationship()
    actor_user: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_inventory_movements_store_created", "store_id", "created_at", "id"),
        Index("ix_inventory_movements_product_created", "product_id", "created_at", "id"),
        Index("ix_inventory_movements_reference", "reference_type", "reference_id"),
        UniqueConstraint("store_id", "reference_type", "reference_id", "movement_type", name="uq_inventory_movements_reference_type_id"),
    )
