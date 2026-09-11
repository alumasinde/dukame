from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.modules.auth.models.identity import User
    from app.modules.rbac.models.rbac import TenantRole
    from app.modules.tenancy.models.business_type import BusinessType


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    business_type_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("business_types.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    memberships: Mapped[list["TenantUser"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    business_type: Mapped["BusinessType | None"] = relationship(back_populates="tenants")


class TenantUser(Base):
    __tablename__ = "tenant_users"
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, server_default="member")
    role_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tenant_roles.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
    role_record: Mapped["TenantRole | None"] = relationship(foreign_keys=[role_id])
    __table_args__ = (
        Index("ix_tenant_users_user_id", "user_id"),
        Index("ix_tenant_users_tenant_status", "tenant_id", "status"),
        Index("ix_tenant_users_role_id", "role_id"),
    )
