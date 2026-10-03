import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundException
from app.models.api_key import ApiKey
from app.services.audit import log as audit_log


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_key() -> tuple[str, str, str]:
    raw = "sk_" + secrets.token_hex(32)
    return raw, _hash_key(raw), raw[:10]


async def create_api_key(db: AsyncSession, user_id: str, name: str, expires_in_days: int | None = None) -> dict:
    raw, key_hash, key_prefix = _generate_key()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    result = {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": raw,
        "key_prefix": api_key.key_prefix,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
    }
    await audit_log(db, user_id, "api_key.create", {"name": name})
    return result


async def list_api_keys(db: AsyncSession, user_id: str) -> list[dict]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "key_prefix": k.key_prefix,
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]


async def revoke_api_key(db: AsyncSession, key_id: str, user_id: str) -> None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise NotFoundException("API key not found")
    key.is_active = False
    await db.commit()
    await audit_log(db, user_id, "api_key.revoke", {"key_id": key_id, "name": key.name})


async def verify_api_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return None
    if key.expires_at and key.expires_at < datetime.now(timezone.utc):
        return None
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return key
