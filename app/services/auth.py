from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
)
from sqlalchemy import select, update

from app.models.backup_code import BackupCode
from app.models.user import User
from app.core.cache import blacklist_token, increment_login_attempts, reset_login_attempts
from app.core.security import verify_password, get_password_hash, decode_token
from app.services.token import create_tokens, verify_refresh_token, revoke_session
from app.services.email_verification import send_verification_email
from app.services.two_factor import verify_totp, verify_backup_code


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
    if settings.REQUIRE_EMAIL_VERIFICATION:
        await send_verification_email(db, user)
    return {"user": user, **tokens}


async def login(
    db: AsyncSession,
    email: str,
    password: str,
    device_info: str | None = None,
    totp_code: str | None = None,
    backup_code: str | None = None,
) -> dict:
    attempts = await increment_login_attempts(email, settings.MAX_LOGIN_ATTEMPTS, settings.LOGIN_LOCKOUT_MINUTES)
    if attempts > settings.MAX_LOGIN_ATTEMPTS:
        raise ForbiddenException(f"Account locked for {settings.LOGIN_LOCKOUT_MINUTES} minutes")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
        raise ForbiddenException("Email not verified")

    if user.is_2fa_enabled:
        if backup_code:
            result = await db.execute(
                select(BackupCode).where(
                    BackupCode.user_id == str(user.id),
                    BackupCode.is_used == False,
                )
            )
            matched = None
            for bc in result.scalars().all():
                if verify_backup_code(backup_code, bc.hashed_code):
                    matched = bc
                    break
            if not matched:
                raise ForbiddenException("Invalid or already used backup code")
            matched.is_used = True
            await db.commit()
        elif not totp_code or not verify_totp(user.totp_secret, totp_code):
            raise ForbiddenException("TOTP code required or invalid")
        elif verify_totp(user.totp_secret, totp_code):
            pass

    await reset_login_attempts(email)
    tokens = await create_tokens(db, str(user.id), device_info)
    return {"user": user, **tokens}


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    session, payload = await verify_refresh_token(db, refresh_token)
    await revoke_session(db, session)

    user_id = payload.get("sub")
    tokens = await create_tokens(db, user_id, session.device_info)
    return tokens


async def logout(db: AsyncSession, access_token: str, refresh_token: str) -> None:
    payload = decode_token(access_token)
    jti = payload.get("jti", "")
    exp = payload.get("exp", 0)
    if jti:
        ttl = max(exp - int(datetime.now(timezone.utc).timestamp()), 0)
        await blacklist_token(jti, ttl)
    session, _ = await verify_refresh_token(db, refresh_token)
    await revoke_session(db, session)