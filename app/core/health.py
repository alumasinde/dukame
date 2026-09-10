from sqlalchemy import text

from app.core.database import engine
from app.core.errors import AppError
from app.core.redis import redis_client


async def readiness_check() -> None:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis_client.ping()
    except Exception as exc:
        raise AppError(
            code="DEPENDENCY_UNAVAILABLE",
            message="A required service is temporarily unavailable.",
            status_code=503,
        ) from exc
