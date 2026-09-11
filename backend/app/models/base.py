from sqlalchemy import BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantScoped:
    """Mixin for models that belong to a tenant."""

    tenant_id: Mapped[int] = mapped_column(BigInteger)
