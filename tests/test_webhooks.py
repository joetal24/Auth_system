from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User


async def _make_admin(db_session: AsyncSession, user_id: str):
    result = await db_session.execute(select(Role).where(Role.name == "admin"))
    role = result.scalar_one_or_none()
    if not role:
        role = Role(name="admin", description="Administrator")
        db_session.add(role)
        await db_session.commit()
    user = await db_session.get(User, user_id)
    user.role_id = role.id
    await db_session.commit()


@pytest.mark.asyncio
async def test_create_webhook(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "admin-webhook@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    await _make_admin(db_session, reg.json()["user"]["id"])

    response = await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["user.created", "user.login"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/hook"
    assert data["events"] == ["user.created", "user.login"]


@pytest.mark.asyncio
async def test_list_webhooks(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "list-webhook@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    await _make_admin(db_session, reg.json()["user"]["id"])

    await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook1", "events": ["user.created"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook2", "events": ["user.login"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get("/api/v1/admin/webhooks", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_delete_webhook(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "del-webhook@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    await _make_admin(db_session, reg.json()["user"]["id"])

    before = await client.get("/api/v1/admin/webhooks", headers={"Authorization": f"Bearer {token}"})
    count_before = len(before.json())

    create = await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/del", "events": ["user.created"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    hid = create.json()["id"]

    delete = await client.delete(f"/api/v1/admin/webhooks/{hid}", headers={"Authorization": f"Bearer {token}"})
    assert delete.status_code == 200

    resp = await client.get("/api/v1/admin/webhooks", headers={"Authorization": f"Bearer {token}"})
    assert len(resp.json()) == count_before


@pytest.mark.asyncio
async def test_webhook_forbidden_for_non_admin(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "nonadmin-webhook@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    response = await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["user.created"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_dispatch_fires_event(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "dispatch-webhook@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    await _make_admin(db_session, reg.json()["user"]["id"])

    await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["user.created"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    with patch("app.services.auth.dispatch_webhook", AsyncMock()) as mock_dispatch:
        await client.post("/api/v1/auth/register", json={"email": "trigger@test.com", "password": "password123"})
        mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_event_rejected(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "bad-event@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    await _make_admin(db_session, reg.json()["user"]["id"])

    response = await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["invalid.event"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
