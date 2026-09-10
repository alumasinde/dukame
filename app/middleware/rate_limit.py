from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.rate_limit import RateLimitExceeded, check_rate_limit
from app.core.redis import redis_client


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if request.url.path in {"/health", "/ready", "/api/v1/health", "/api/v1/health/live"}:
            await self.app(scope, receive, send)
            return

        client_host = request.client.host if request.client else "unknown"
        key = f"ip:{client_host}:{request.method}:{request.url.path}"
        try:
            await check_rate_limit(key)
        except RateLimitExceeded:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                    }
                },
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
            await response(scope, receive, send)
            return
        except Exception:
            if settings.is_production:
                response = JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_UNAVAILABLE",
                            "message": "Request protection is temporarily unavailable.",
                        }
                    },
                    headers={"Retry-After": "5"},
                )
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
