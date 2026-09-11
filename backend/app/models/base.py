from typing import Any

from sqlalchemy import BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import Select


class Base(DeclarativeBase):
    pass


class TenantScoped:
    """
    Mixin for models that belong to a tenant.

    Tenant filtering remains explicit in repositories/services so query scope is
    visible at the data-access boundary.
    """

    tenant_id: Mapped[int] = mapped_column(BigInteger)

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        original_select = Select.select

        def scoped_select(cls_arg: Any, *args: Any, **kwargs: Any) -> Select[Any]:
            return original_select(cls_arg, *args, **kwargs)

        _ = scoped_select
