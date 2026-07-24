import secrets

import bcrypt
import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import ForbiddenException, UnauthorizedException
from app.models.backup_code import BackupCode
from app.models.user import User
from app.core.security import verify_password


def _get_totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret, issuer=settings.APP_NAME)


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    return _get_totp(secret).provisioning_uri(name=email, issuer_name=settings.APP_NAME)


def verify_totp(secret: str, code: str) -> bool:
    return _get_totp(secret).verify(code, valid_window=1)


def generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(10) for _ in range(count)]


def hash_backup_code(code: str) -> str:
    return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()


def verify_backup_code(code: str, hashed: str) -> bool:
    return bcrypt.checkpw(code.encode(), hashed.encode())


async def enable_2fa(db: AsyncSession, user: User) -> dict:
    secret = generate_totp_secret()
    user.totp_secret = secret
    raw_codes = generate_backup_codes()
    for code in raw_codes:
        db.add(BackupCode(user_id=str(user.id), hashed_code=hash_backup_code(code)))
    await db.commit()
    await db.refresh(user)
    return {
        "secret": secret,
        "uri": get_totp_uri(secret, user.email),
        "backup_codes": raw_codes,
    }


async def verify_2fa_setup(db: AsyncSession, user: User, code: str) -> None:
    if not user.totp_secret:
        raise UnauthorizedException("2FA not initiated")
    if not verify_totp(user.totp_secret, code):
        raise ForbiddenException("Invalid TOTP code")
    user.is_2fa_enabled = True
    await db.commit()


async def disable_2fa(db: AsyncSession, user: User, password: str, totp_code: str | None, backup_code: str | None) -> None:
    if not verify_password(password, user.hashed_password):
        raise ForbiddenException("Invalid password")
    if totp_code:
        if not verify_totp(user.totp_secret, totp_code):
            raise ForbiddenException("Invalid TOTP code")
    elif backup_code:
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
    else:
        raise ForbiddenException("TOTP code or backup code required")
    user.totp_secret = None
    user.is_2fa_enabled = False
    result = await db.execute(select(BackupCode).where(BackupCode.user_id == str(user.id)))
    for bc in result.scalars().all():
        await db.delete(bc)
    await db.commit()
