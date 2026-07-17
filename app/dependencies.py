from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import ForbiddenException, UnauthorizedException
from app.services.token import verify_access_token
from app.services.user import get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    payload = await verify_access_token(token)
    user = await get_user(db, payload.get("sub"))
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")
    return user


async def get_current_admin(
    current_user=Depends(get_current_user),
):
    if not current_user.role or current_user.role.name != "admin":
        raise ForbiddenException("Admin access required")
    return current_user