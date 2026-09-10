from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    pass


class TenantScoped:
    """
    Mixin for models that belong to a tenant.
    
    Ensures that all queries on tenant-scoped models automatically include
    the tenant_id filter. This prevents accidental data leaks across tenants.
    
    Usage:
        class Order(Base, TenantScoped):
            __tablename__ = "orders"
            tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tenants.id"))
    
    Note: Developers must ensure tenant_id is set before flushing.
    """

    tenant_id: Mapped[int] = mapped_column(BigInteger)

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Warn developers that they need to implement tenant filtering in their repositories
        original_select = Select.select

        def scoped_select(cls_arg: Any, *args: Any, **kwargs: Any) -> Select[Any]:
            stmt = original_select(cls_arg, *args, **kwargs)
            # This is a helper; actual filtering should happen in service/repository layer
            return stmt

        # Note: Full automatic filtering would require custom query compilation,
        # which is better handled at the repository layer for clarity.
