import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models.base import Base
from app.modules.auth.models.identity import AuthSession, User  # noqa: F401
from app.modules.auth.models.tokens import PasswordResetToken, VerificationToken  # noqa: F401
from app.modules.catalogue.models import Category, Product, ProductMedia, ProductOption, ProductOptionValue, ProductVariant, ProductVariantOptionValue, Store  # noqa: F401
from app.modules.commerce.models import Cart, CartItem, IdempotencyKey, Order, OrderItem, OrderNotification, OrderStatus, OrderStatusHistory, OrderStatusTransition, Payment, PaymentAttempt, PaymentEvent, PaymentMethod  # noqa: F401
from app.modules.rbac.models.rbac import Permission, TenantRole, TenantRolePermission  # noqa: F401
from app.modules.subscriptions.models.subscription import Plan, PlanFeature, Subscription, SubscriptionEvent  # noqa: F401
from app.modules.tenancy.models.business_type import BusinessType  # noqa: F401
from app.modules.tenancy.models.tenant import Tenant, TenantUser  # noqa: F401

config = context.config

database_url = str(settings.database_url)
for driver in ("mysql://", "mysql+pymysql://"):
    if database_url.startswith(driver):
        database_url = database_url.replace(driver, "mysql+aiomysql://", 1)
        break
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
