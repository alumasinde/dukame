from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.errors import install_exception_handlers
from app.core.health import readiness_check
from app.core.logging import configure_logging
from app.core.redis import redis_client
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    try:
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
)
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


install_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready() -> dict[str, str]:
    await readiness_check()
    return {"status": "ready"}
