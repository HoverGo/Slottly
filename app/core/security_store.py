"""Хранилище rate limit и brute-force: in-memory или Redis"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.redis_client import get_redis, redis_enabled

RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  if oldest[2] then
    return math.ceil(window - (now - tonumber(oldest[2])))
  end
  return window
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window + 1)
return 0
"""


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: int


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, rule: RateLimitRule) -> None:
        now = time.monotonic()
        cutoff = now - rule.window_seconds
        async with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= rule.max_requests:
                retry_after = max(1, int(rule.window_seconds - (now - bucket[0])))
                self._raise_limit(retry_after)
            bucket.append(now)

    async def reset(self) -> None:
        async with self._lock:
            self._hits.clear()

    @staticmethod
    def _raise_limit(retry_after: int) -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Попробуйте позже",
            headers={"Retry-After": str(retry_after)},
        )


class RedisRateLimitStore:
    async def check(self, key: str, rule: RateLimitRule) -> None:
        redis = await get_redis()
        if redis is None:
            return
        now = time.time()
        member = f"{now}:{id(key)}"
        retry_after = await redis.eval(
            RATE_LIMIT_LUA,
            1,
            f"rl:{key}",
            str(now),
            str(rule.window_seconds),
            str(rule.max_requests),
            member,
        )
        if retry_after and int(retry_after) > 0:
            MemoryRateLimitStore._raise_limit(int(retry_after))

    async def reset(self) -> None:
        redis = await get_redis()
        if redis is None:
            return
        keys = [key async for key in redis.scan_iter("rl:*")]
        if keys:
            await redis.delete(*keys)


class MemoryBruteForceStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, float]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def assert_not_locked(self, key: str, lockout_seconds: float) -> None:
        now = time.monotonic()
        async with self._lock:
            locked_until = self._records[key].get("locked_until", 0.0)
            if locked_until > now:
                wait_min = max(1, int((locked_until - now) / 60) + 1)
                from app.core.exceptions import AppError

                raise AppError(
                    f"Слишком много неудачных попыток входа. Повторите через {wait_min} мин.",
                    status_code=429,
                )

    async def register_failure(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: float,
        lockout_seconds: float,
    ) -> None:
        now = time.monotonic()
        async with self._lock:
            record = self._records[key]
            last = record.get("last_failure", 0.0)
            failures = record.get("failures", 0.0)
            if now - last > window_seconds:
                failures = 0.0
            failures += 1
            record["failures"] = failures
            record["last_failure"] = now
            if failures >= max_attempts:
                record["locked_until"] = now + lockout_seconds
                record["failures"] = 0.0

    async def register_success(self, key: str) -> None:
        async with self._lock:
            self._records.pop(key, None)

    async def reset(self) -> None:
        async with self._lock:
            self._records.clear()


class RedisBruteForceStore:
    async def assert_not_locked(self, key: str, lockout_seconds: float) -> None:
        redis = await get_redis()
        if redis is None:
            return
        lock_key = f"bf:lock:{key}"
        ttl = await redis.ttl(lock_key)
        if ttl and ttl > 0:
            from app.core.exceptions import AppError

            wait_min = max(1, int(ttl / 60) + 1)
            raise AppError(
                f"Слишком много неудачных попыток входа. Повторите через {wait_min} мин.",
                status_code=429,
            )

    async def register_failure(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: float,
        lockout_seconds: float,
    ) -> None:
        redis = await get_redis()
        if redis is None:
            return
        fail_key = f"bf:fail:{key}"
        count = await redis.incr(fail_key)
        if count == 1:
            await redis.expire(fail_key, int(window_seconds))
        if count >= max_attempts:
            await redis.setex(f"bf:lock:{key}", int(lockout_seconds), "1")
            await redis.delete(fail_key)

    async def register_success(self, key: str) -> None:
        redis = await get_redis()
        if redis is None:
            return
        await redis.delete(f"bf:fail:{key}", f"bf:lock:{key}")

    async def reset(self) -> None:
        redis = await get_redis()
        if redis is None:
            return
        fail_keys = [k async for k in redis.scan_iter("bf:fail:*")]
        lock_keys = [k async for k in redis.scan_iter("bf:lock:*")]
        all_keys = fail_keys + lock_keys
        if all_keys:
            await redis.delete(*all_keys)


def create_rate_limit_store():
    if redis_enabled():
        return RedisRateLimitStore()
    return MemoryRateLimitStore()


def create_brute_force_store():
    if redis_enabled():
        return RedisBruteForceStore()
    return MemoryBruteForceStore()
