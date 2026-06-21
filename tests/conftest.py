import pytest
from httpx import ASGITransport, AsyncClient

from app.core.brute_force import login_brute_force
from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    await rate_limiter.reset()
    await login_brute_force.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await rate_limiter.reset()
    await login_brute_force.reset()


@pytest.fixture
def anyio_backend():
    return "asyncio"
