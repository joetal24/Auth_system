from unittest.mock import ANY

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User
from app.services.token import create_tokens


async def _make_admin(db: AsyncSession) -> str:
    result = await db.execute(select(Role).where(Role.name == "admin"))
    role = result.scalar_one_or_none()
    if not role:
        role = Role(name="admin", description="Administrator")
        db.add(role)
        await db.commit()

    user = User(
        email="admin@example.com",
        hashed_password="irrelevant",
        role_id=str(role.id),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = await create_tokens(db, str(user.id))
    return tokens["access_token"]


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_admin(client: AsyncClient, db_session: AsyncSession):
    token = await _make_admin(db_session)
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_users_forbidden(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "getuser@example.com", "password": "password123"},
    )
    data = reg.json()
    response = await client.get(
        f"/api/v1/users/{data['user']['id']}",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "getuser@example.com"


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "notfound-test@example.com", "password": "password123"},
    )
    response = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    )
    assert response.status_code == 404
