import pytest
from fastapi import Request
from httpx import AsyncClient

from app.core.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_disabled_without_redis():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("localhost", 8000),
    }
    request = Request(scope)
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    result = await limiter(request)
    assert result is None


@pytest.mark.asyncio
async def test_rate_limited_endpoint_no_crash(client: AsyncClient):
    for _ in range(10):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": f"ratelimit{_}@example.com", "password": "password123"},
        )
        assert response.status_code in (200, 409)


@pytest.mark.asyncio
async def test_rate_limiter_graceful_degradation(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit-none@example.com", "password": "test"},
    )
    assert response.status_code == 401
