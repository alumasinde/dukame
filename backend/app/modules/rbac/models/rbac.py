from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TenantRole(Base):
    __tablename__ = "tenant_roles"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    permissions: Mapped[list["TenantRolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_tenant_roles_tenant_slug"), Index("ix_tenant_roles_tenant", "tenant_id"))


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    role_links: Mapped[list["TenantRolePermission"]] = relationship(back_populates="permission", cascade="all, delete-orphan")


class TenantRolePermission(Base):
    __tablename__ = "tenant_role_permissions"
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tenant_roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    role: Mapped[TenantRole] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_links")
