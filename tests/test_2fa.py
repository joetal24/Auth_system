import pyotp
import pytest
from httpx import AsyncClient

from app.main import app
from app.services.auth import login as login_service
from app.services.auth import register as register_user
from app.services.two_factor import enable_2fa, verify_2fa_setup


@pytest.mark.asyncio
async def test_enable_2fa(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "2fa-enable@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "uri" in data
    assert "backup_codes" in data
    assert len(data["backup_codes"]) == 10


@pytest.mark.asyncio
async def test_verify_2fa_setup(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "2fa-verify@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    enable = await client.post(
        "/api/v1/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
    )
    secret = enable.json()["secret"]
    valid_code = pyotp.TOTP(secret).now()

    response = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"totp_code": valid_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "2FA enabled successfully"}


@pytest.mark.asyncio
async def test_verify_2fa_invalid_code(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "2fa-badcode@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    await client.post(
        "/api/v1/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"totp_code": "000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_with_totp(client: AsyncClient, db_session):
    user = await register_user(db_session, "2fa-login@example.com", "password123")
    result = await enable_2fa(db_session, user["user"])
    await verify_2fa_setup(db_session, user["user"], pyotp.TOTP(result["secret"]).now())

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa-login@example.com", "password": "password123", "totp_code": pyotp.TOTP(result["secret"]).now()},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_without_totp_returns_403(client: AsyncClient, db_session):
    user = await register_user(db_session, "2fa-nototp@example.com", "password123")
    result = await enable_2fa(db_session, user["user"])
    await verify_2fa_setup(db_session, user["user"], pyotp.TOTP(result["secret"]).now())

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa-nototp@example.com", "password": "password123"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_with_backup_code(client: AsyncClient, db_session):
    user = await register_user(db_session, "2fa-backup@example.com", "password123")
    result = await enable_2fa(db_session, user["user"])
    await verify_2fa_setup(db_session, user["user"], pyotp.TOTP(result["secret"]).now())
    backup_code = result["backup_codes"][0]

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa-backup@example.com", "password": "password123", "backup_code": backup_code},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_disable_2fa(client: AsyncClient, db_session):
    user = await register_user(db_session, "2fa-disable@example.com", "password123")
    result = await enable_2fa(db_session, user["user"])
    await verify_2fa_setup(db_session, user["user"], pyotp.TOTP(result["secret"]).now())

    reg = await client.post(
        "/api/v1/auth/login",
        json={"email": "2fa-disable@example.com", "password": "password123", "totp_code": pyotp.TOTP(result["secret"]).now()},
    )
    token = reg.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/2fa/disable",
        json={"password": "password123", "totp_code": pyotp.TOTP(result["secret"]).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "2FA disabled successfully"}
