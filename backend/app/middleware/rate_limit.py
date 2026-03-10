import time

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.db.redis import get_redis_cache


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding window rate limiter using Redis."""

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health endpoints
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Extract identifier: authenticated user or IP
        client_ip = request.client.host if request.client else "unknown"

        # Try to get user ID from auth header (lightweight, no DB call)
        identifier = f"rl:{client_ip}"

        try:
            redis = get_redis_cache()
            now = time.time()
            window_key = f"{identifier}:{int(now // 60)}"

            count = await redis.incr(window_key)
            if count == 1:
                await redis.expire(window_key, 120)

            if count > self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
        except HTTPException:
            raise
        except Exception:
            # If Redis is down, allow the request through
            pass

        return await call_next(request)
