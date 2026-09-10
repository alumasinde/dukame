from sqlalchemy import text

from app.core.database import engine
from app.core.redis import redis_client


async def readiness_check() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    await redis_client.ping()
