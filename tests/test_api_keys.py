import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "apikey@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "my-key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "my-key"
    assert data["key"].startswith("sk_")
    assert data["key_prefix"] == data["key"][:10]


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "list-apikey@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    await client.post("/api/v1/auth/api-keys", json={"name": "key1"}, headers={"Authorization": f"Bearer {token}"})
    await client.post("/api/v1/auth/api-keys", json={"name": "key2"}, headers={"Authorization": f"Bearer {token}"})

    response = await client.get("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    keys = response.json()["api_keys"]
    assert len(keys) == 2
    assert keys[0]["name"] == "key2"
    assert "key" not in keys[0]


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "revoke-apikey@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    create = await client.post("/api/v1/auth/api-keys", json={"name": "to-revoke"}, headers={"Authorization": f"Bearer {token}"})
    key_id = create.json()["id"]

    response = await client.delete(f"/api/v1/auth/api-keys/{key_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # deleted key should not show as active
    keys = await client.get("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {token}"})
    assert keys.json()["api_keys"][0]["is_active"] is False


@pytest.mark.asyncio
async def test_authenticate_with_api_key(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "keyauth@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    create = await client.post("/api/v1/auth/api-keys", json={"name": "auth-key"}, headers={"Authorization": f"Bearer {token}"})
    api_key = create.json()["key"]

    response = await client.get("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_revoked_api_key_cannot_authenticate(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "revoked-key@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    create = await client.post("/api/v1/auth/api-keys", json={"name": "revoked"}, headers={"Authorization": f"Bearer {token}"})
    api_key = create.json()["key"]
    key_id = create.json()["id"]

    await client.delete(f"/api/v1/auth/api-keys/{key_id}", headers={"Authorization": f"Bearer {token}"})

    response = await client.get("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_format_rejected(client: AsyncClient):
    response = await client.get("/api/v1/auth/api-keys", headers={"Authorization": "Bearer not-an-api-key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_api_key_with_expiry(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "expiry-key@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "time-limited", "expires_in_days": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["expires_at"] is not None
