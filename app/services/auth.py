from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    ConflictException,
    UnauthorizedException,
)
from app.models.user import User
from app.services.token import create_tokens, verify_refresh_token, revoke_session
from app.core.security import verify_password, get_password_hash


async def register(
    db: AsyncSession,
    email: str,
    password: str,
    device_info: str | None = None,
) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ConflictException("Email already registered")

    user = User(
        email=email,
        hashed_password=get_password_hash(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = await create_tokens(db, str(user.id), device_info)
    return {"user": user, **tokens}


async def login(
    db: AsyncSession,
    email: str,
    password: str,
    device_info: str | None = None,
) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")

    tokens = await create_tokens(db, str(user.id), device_info)
    return {"user": user, **tokens}


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    session, payload = await verify_refresh_token(db, refresh_token)
    await revoke_session(db, session)

    user_id = payload.get("sub")
    tokens = await create_tokens(db, user_id, session.device_info)
    return tokens


async def logout(db: AsyncSession, refresh_token: str) -> None:
    session, _ = await verify_refresh_token(db, refresh_token)
    await revoke_session(db, session)