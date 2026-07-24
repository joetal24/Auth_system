import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sessions-list@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert len(data["sessions"]) >= 1
    assert any(s["is_current"] for s in data["sessions"])


@pytest.mark.asyncio
async def test_revoke_session(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sessions-revoke@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    list_resp = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = list_resp.json()["sessions"][0]["id"]

    response = await client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Session revoked"}

    list_resp2 = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(list_resp2.json()["sessions"]) == 0


@pytest.mark.asyncio
async def test_revoke_session_not_owned(client: AsyncClient):
    reg1 = await client.post(
        "/api/v1/auth/register",
        json={"email": "sessions-owner@example.com", "password": "password123"},
    )
    reg2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "sessions-thief@example.com", "password": "password123"},
    )
    token2 = reg2.json()["access_token"]

    list_resp1 = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {reg1.json()['access_token']}"},
    )
    session_id = list_resp1.json()["sessions"][0]["id"]

    response = await client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revoke_others(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sessions-others@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    # login again to create a second session
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "sessions-others@example.com", "password": "password123"},
    )
    token2 = login.json()["access_token"]

    list_resp = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(list_resp.json()["sessions"]) == 2

    response = await client.post(
        "/api/v1/auth/sessions/revoke-others",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    list_resp2 = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(list_resp2.json()["sessions"]) == 1
    assert list_resp2.json()["sessions"][0]["is_current"] is True
