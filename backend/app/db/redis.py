from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_cache_pool: aioredis.Redis[str] | None = None


def get_redis_cache() -> aioredis.Redis[str]:
    global _cache_pool
    if _cache_pool is None:
        _cache_pool = aioredis.from_url(
            settings.redis_cache_url,
            decode_responses=True,
            max_connections=20,
        )
    return _cache_pool


async def close_redis() -> None:
    global _cache_pool
    if _cache_pool is not None:
        await _cache_pool.close()
        _cache_pool = None
