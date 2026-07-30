from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import UnauthorizedException
from app.services.auth import register as register_user
from app.services.password_reset import forgot_password, reset_password

VALID_TOKEN = "valid-reset-token-12345678901234567890"


@pytest.mark.asyncio
async def test_forgot_password_unknown_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_forgot_password_known_email(client: AsyncClient, db_session: AsyncSession):
    await register_user(db_session, "resetpw@example.com", "password123")
    with patch("app.services.password_reset.set_value"):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "resetpw@example.com"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "reset_token" in data or data["message"] == "Password reset link sent if account exists"


@pytest.mark.asyncio
async def test_reset_password(db_session: AsyncSession):
    user = await register_user(db_session, "reset-exec@example.com", "password123")
    with patch("app.services.password_reset.set_value"):

        token = await forgot_password(db_session, "reset-exec@example.com")

    with patch("app.services.password_reset.get_value", return_value=str(user["user"].id)):
        with patch("app.services.password_reset.delete_value"):
            await reset_password(db_session, token, "newpassword123")

    # verify new password works
    from app.core.security import verify_password
    assert verify_password("newpassword123", user["user"].hashed_password)


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    with patch("app.services.password_reset.get_value", return_value=None):
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "fake-token", "new_password": "newpassword123"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_short_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "some-token", "new_password": "short"},
    )
    assert response.status_code == 422
