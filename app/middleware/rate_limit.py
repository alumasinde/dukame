from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rate_limit import RateLimitExceeded, check_rate_limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = f"ip:{request.client.host if request.client else 'unknown'}:{request.method}:{request.url.path}"
        try:
            await check_rate_limit(key)
        except RateLimitExceeded:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limit_exceeded", "message": "Too many requests"}},
                headers={"Retry-After": "60"},
            )
        response = await call_next(request)
        return response
