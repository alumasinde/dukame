from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def get_async_database_url() -> str:
    url = str(settings.database_url)
    for driver in ("mysql://", "mysql+pymysql://"):
        if url.startswith(driver):
            return url.replace(driver, "mysql+aiomysql://", 1)
    return url


engine = create_async_engine(
    get_async_database_url(),
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_recycle=settings.database_pool_recycle,
    pool_timeout=settings.database_pool_timeout,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
