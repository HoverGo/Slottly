"""Защита от перебора паролей при входе. Redis — общий счётчик для нескольких воркеров"""

from fastapi import Request

from app.core.config import settings
from app.core.rate_limit import client_ip
from app.core.security_store import create_brute_force_store


class LoginBruteForceProtector:
    def __init__(self) -> None:
        self._store = create_brute_force_store()

    def _key(self, email: str, ip: str) -> str:
        return f"{email.strip().lower()}:{ip}"

    async def assert_can_attempt(self, email: str, request: Request) -> None:
        if not settings.brute_force_enabled:
            return
        key = self._key(email, client_ip(request))
        lockout = settings.login_lockout_minutes * 60
        await self._store.assert_not_locked(key, lockout)

    async def register_failure(self, email: str, request: Request) -> None:
        if not settings.brute_force_enabled:
            return
        key = self._key(email, client_ip(request))
        await self._store.register_failure(
            key,
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_attempt_window_minutes * 60,
            lockout_seconds=settings.login_lockout_minutes * 60,
        )

    async def register_success(self, email: str, request: Request) -> None:
        if not settings.brute_force_enabled:
            return
        key = self._key(email, client_ip(request))
        await self._store.register_success(key)

    async def reset(self) -> None:
        await self._store.reset()


login_brute_force = LoginBruteForceProtector()
