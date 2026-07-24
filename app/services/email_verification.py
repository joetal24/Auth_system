import logging
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import set_value, get_value, delete_value
from app.exceptions import UnauthorizedException
from app.models.user import User
from app.services.email import send_email, build_verification_email

logger = logging.getLogger(__name__)

VERIFY_PREFIX = "verify:"
VERIFY_TTL = 86400  # 24 hours


async def create_verification_token(user_id: str) -> str | None:
    token = secrets.token_urlsafe(32)
    try:
        await set_value(f"{VERIFY_PREFIX}{token}", user_id, VERIFY_TTL)
        return token
    except RuntimeError:
        logger.warning("Redis unavailable, verification token not stored")
        return None


async def send_verification_email(db: AsyncSession, user: User) -> None:
    if not settings.SMTP_HOST and not settings.DEBUG:
        return
    token = await create_verification_token(str(user.id))
    if token is None:
        return
    if not settings.SMTP_HOST:
        return
    subject, html = build_verification_email(token)
    await send_email(user.email, subject, html)


async def verify_email(token: str) -> str | None:
    try:
        return await get_value(f"{VERIFY_PREFIX}{token}")
    except RuntimeError:
        logger.warning("Redis unavailable, cannot verify token")
        return None


async def confirm_verification(token: str, db: AsyncSession) -> None:
    user_id = await verify_email(token)
    if not user_id:
        raise UnauthorizedException("Invalid or expired verification token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("User not found")

    user.is_verified = True
    await db.commit()
    await delete_value(f"{VERIFY_PREFIX}{token}")
