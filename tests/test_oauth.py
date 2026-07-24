from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.services.oauth import oauth_login


@pytest.mark.asyncio
async def test_oauth_google_url(client: AsyncClient):
    response = await client.get("/api/v1/auth/oauth/google")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "accounts.google.com" in data["url"]


@pytest.mark.asyncio
async def test_oauth_github_url(client: AsyncClient):
    response = await client.get("/api/v1/auth/oauth/github")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "github.com/login/oauth/authorize" in data["url"]


@pytest.mark.asyncio
async def test_oauth_login_creates_user(db_session):
    mock_profile = {"id": "12345", "email": "oauth-google@example.com", "name": "OAuth User"}

    with patch("app.services.oauth.google_exchange_code", return_value=mock_profile):
        result = await oauth_login(db_session, "google", "valid-code")

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"].email == "oauth-google@example.com"
    assert result["user"].google_id == "12345"
    assert result["user"].is_verified is True
    assert result["user"].hashed_password is None

    with patch("app.services.oauth.google_exchange_code", return_value=mock_profile):
        result2 = await oauth_login(db_session, "google", "valid-code")
    assert result2["user"].id == result["user"].id


@pytest.mark.asyncio
async def test_oauth_links_existing_email(db_session):
    from app.services.auth import register as register_user

    user = await register_user(db_session, "link-oauth@example.com", "password123")
    existing_id = user["user"].id

    mock_profile = {"id": "67890", "email": "link-oauth@example.com", "name": "Linked"}

    with patch("app.services.oauth.google_exchange_code", return_value=mock_profile):
        result = await oauth_login(db_session, "google", "valid-code")

    assert result["user"].id == existing_id
    assert result["user"].google_id == "67890"


@pytest.mark.asyncio
async def test_oauth_user_cannot_password_login(client: AsyncClient, db_session):
    mock_profile = {"id": "99999", "email": "oauth-nopw@example.com", "name": "NoPW"}

    with patch("app.services.oauth.google_exchange_code", return_value=mock_profile):
        await oauth_login(db_session, "google", "valid-code")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "oauth-nopw@example.com", "password": "anything"},
    )
    assert response.status_code == 401
