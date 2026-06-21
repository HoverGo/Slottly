import pytest
from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security_store import MemoryBruteForceStore


def _request(ip: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [],
        "client": (ip, 12345),
        "server": ("test", 80),
        "scheme": "http",
        "query_string": b"",
        "root_path": "",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_brute_force_locks_after_max_attempts(monkeypatch):
    monkeypatch.setattr(settings, "login_max_attempts", 3)
    monkeypatch.setattr(settings, "login_lockout_minutes", 15)
    store = MemoryBruteForceStore()
    request = _request()
    key = "user@example.com:10.0.0.1"

    for _ in range(3):
        await store.register_failure(
            key,
            max_attempts=3,
            window_seconds=900,
            lockout_seconds=900,
        )

    with pytest.raises(AppError) as exc:
        await store.assert_not_locked(key, 900)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_brute_force_clears_on_success():
    store = MemoryBruteForceStore()
    key = "ok@example.com:10.0.0.1"
    await store.register_failure(key, max_attempts=5, window_seconds=900, lockout_seconds=900)
    await store.register_success(key)
    await store.assert_not_locked(key, 900)
