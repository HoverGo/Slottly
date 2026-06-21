import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_security_headers_on_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_request_size_limit_rejects_large_body(client: AsyncClient):
    huge = b"x" * (settings.max_request_body_mb * 1024 * 1024 + 1)
    response = await client.post(
        "/api/v1/auth/register",
        content=huge,
        headers={"Content-Type": "application/json", "Content-Length": str(len(huge))},
    )
    assert response.status_code == 413
