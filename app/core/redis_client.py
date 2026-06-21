"""Async Redis-клиент для rate limit и brute-force (общий для воркеров)"""

from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


def redis_enabled() -> bool:
    return bool(settings.redis_url.strip())


async def get_redis() -> Redis | None:
    global _redis
    if not redis_enabled():
        return None
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
