from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.modules.rbac.models.rbac import Permission

if TYPE_CHECKING:
    from app.modules.commerce.models.order_status import OrderStatus


class OrderStatusTransition(Base):
    __tablename__ = "order_status_transitions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    from_status_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_statuses.id", ondelete="CASCADE"), nullable=False)
    to_status_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_statuses.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("permissions.id", ondelete="RESTRICT"), nullable=False)

    from_status: Mapped["OrderStatus"] = relationship(foreign_keys=[from_status_id])
    to_status: Mapped["OrderStatus"] = relationship(foreign_keys=[to_status_id])
    permission: Mapped["Permission"] = relationship()

    __table_args__ = (
        UniqueConstraint("from_status_id", "to_status_id", name="uq_order_status_transition"),
        Index("ix_order_status_transitions_from", "from_status_id"),
        Index("ix_order_status_transitions_permission", "permission_id"),
    )
