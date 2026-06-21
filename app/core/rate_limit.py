"""Rate limiting по IP и пути. Redis — общий счётчик для нескольких воркеров"""

from fastapi import Request

from app.core.config import settings
from app.core.security_store import RateLimitRule, create_rate_limit_store

# (префикс пути, правило) — первое совпадение побеждает
DEFAULT_RULES: tuple[tuple[str, RateLimitRule], ...] = (
    ("/api/v1/auth/login", RateLimitRule(10, 60)),
    ("/api/v1/auth/register", RateLimitRule(5, 3600)),
    ("/api/v1/auth/invites/", RateLimitRule(20, 60)),
    ("/api/v1/public/booking/", RateLimitRule(60, 60)),
    ("/api/v1/payments/webhook/", RateLimitRule(120, 60)),
    ("/api/v1/", RateLimitRule(300, 60)),
)


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def rule_for_path(path: str) -> RateLimitRule:
    for prefix, rule in DEFAULT_RULES:
        if path.startswith(prefix):
            return rule
    return RateLimitRule(600, 60)


class RateLimiter:
    def __init__(self) -> None:
        self._store = create_rate_limit_store()

    async def check(self, key: str, rule: RateLimitRule) -> None:
        await self._store.check(key, rule)

    async def reset(self) -> None:
        await self._store.reset()


rate_limiter = RateLimiter()


async def enforce_rate_limit(request: Request) -> None:
    if not settings.rate_limit_enabled:
        return
    path = request.url.path
    rule = rule_for_path(path)
    ip = client_ip(request)
    key = f"{ip}:{path.split('/')[1:4]}"
    await rate_limiter.check(key, rule)
