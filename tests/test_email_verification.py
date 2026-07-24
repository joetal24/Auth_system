import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import UnauthorizedException
from app.services.auth import register as register_user
from app.services.email_verification import create_verification_token, verify_email, confirm_verification


@pytest.mark.asyncio
async def test_register_returns_is_verified(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "verify-user@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["is_verified"] is False


@pytest.mark.asyncio
async def test_verify_email_token_not_available(db_session: AsyncSession):
    user = await register_user(db_session, "no-token@example.com", "password123")
    token = await create_verification_token(str(user["user"].id))
    assert token is None  # Redis unavailable in tests

    user_id = await verify_email("nonexistent")
    assert user_id is None

    with pytest.raises(UnauthorizedException):
        await confirm_verification("nonexistent", db_session)


@pytest.mark.asyncio
async def test_verify_email_endpoint_invalid_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/verify-email?token=fake-token")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_resend_verification(client: AsyncClient, db_session: AsyncSession):
    await register_user(db_session, "resend@example.com", "password123")
    response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Verification email sent if account exists"}


@pytest.mark.asyncio
async def test_resend_verification_unknown_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Verification email sent if account exists"}
