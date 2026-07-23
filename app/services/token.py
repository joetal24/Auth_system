import hashlib
from datetime import datetime, timezone, timedelta

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import is_token_blacklisted
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.exceptions import UnauthorizedException
from app.models.session import Session


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_tokens(
    db: AsyncSession,
    user_id: str,
    device_info: str | None = None,
) -> dict:
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})

    session = Session(
        user_id=user_id,
        refresh_token_hash=_hash_token(refresh_token),
        device_info=device_info,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(session)
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token}


async def verify_access_token(token: str) -> dict:
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedException("Invalid or expired access token")
    if payload.get("type") == "refresh":
        raise UnauthorizedException("Invalid token type")
    if await is_token_blacklisted(payload.get("jti", "")):
        raise UnauthorizedException("Token has been revoked")
    return payload


async def verify_refresh_token(db: AsyncSession, token: str) -> tuple[Session, dict]:
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedException("Invalid or expired refresh token")
    result = await db.execute(
        select(Session).where(
            Session.is_revoked == False,
            Session.refresh_token_hash == _hash_token(token),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise UnauthorizedException("Refresh token not found or revoked")
    return session, payload


async def revoke_session(db: AsyncSession, session: Session) -> None:
    session.is_revoked = True
    await db.commit()