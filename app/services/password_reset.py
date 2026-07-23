import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import set_value, get_value, delete_value
from app.core.security import get_password_hash
from app.exceptions import NotFoundException, UnauthorizedException
from app.models.user import User

RESET_PREFIX = "pwdreset:"
RESET_TTL = 900  # 15 minutes


async def forgot_password(db: AsyncSession, email: str) -> str:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("No account with that email")

    token = secrets.token_urlsafe(32)
    await set_value(f"{RESET_PREFIX}{token}", str(user.id), RESET_TTL)
    return token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    user_id = await get_value(f"{RESET_PREFIX}{token}")
    if not user_id:
        raise UnauthorizedException("Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("User not found")

    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    await delete_value(f"{RESET_PREFIX}{token}")
