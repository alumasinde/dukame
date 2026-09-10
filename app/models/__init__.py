from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.identity import Tenant, TenantUser, User

__all__ = ["Base", "Tenant", "TenantUser", "User"]
