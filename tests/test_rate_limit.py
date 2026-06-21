import pytest
from fastapi import HTTPException

from app.core.security_store import MemoryBruteForceStore, MemoryRateLimitStore, RateLimitRule


@pytest.mark.asyncio
async def test_rate_limit_allows_under_threshold():
    limiter = MemoryRateLimitStore()
    rule = RateLimitRule(max_requests=3, window_seconds=60)
    for _ in range(3):
        await limiter.check("test-key", rule)


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_threshold():
    limiter = MemoryRateLimitStore()
    rule = RateLimitRule(max_requests=2, window_seconds=60)
    await limiter.check("key", rule)
    await limiter.check("key", rule)
    with pytest.raises(HTTPException) as exc:
        await limiter.check("key", rule)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers
