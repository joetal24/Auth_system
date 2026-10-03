import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
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
async def test_audit_log_created_on_register(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "audit-reg@test.com", "password": "password123"})
    uid = reg.json()["user"]["id"]

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "user.register", AuditLog.user_id == uid)
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert "audit-reg@test.com" in log.details


@pytest.mark.asyncio
async def test_audit_log_created_on_login(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "audit-login@test.com", "password": "password123"})
    uid = reg.json()["user"]["id"]
    await client.post("/api/v1/auth/login", json={"email": "audit-login@test.com", "password": "password123"})

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "user.login", AuditLog.user_id == uid)
    )
    log = result.scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_admin_can_query_audit_logs(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "audit-admin@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    uid = reg.json()["user"]["id"]

    await _make_admin(db_session, uid)

    response = await client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_audit_log_filter_by_action(client: AsyncClient, db_session: AsyncSession):
    reg = await client.post("/api/v1/auth/register", json={"email": "audit-filter@test.com", "password": "password123"})
    token = reg.json()["access_token"]
    uid = reg.json()["user"]["id"]

    await _make_admin(db_session, uid)

    response = await client.get(
        "/api/v1/admin/audit-logs?action=user.register",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    for log in response.json():
        assert log["action"] == "user.register"


@pytest.mark.asyncio
async def test_audit_log_forbidden_for_non_admin(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "audit-nonadmin@test.com", "password": "password123"})
    token = reg.json()["access_token"]

    response = await client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
