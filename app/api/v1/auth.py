from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limit import RateLimiter
from app.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services import auth as auth_service
from app.services import password_reset as password_reset_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=5, window_seconds=60)),
):
    return await auth_service.register(db, body.email, body.password)


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=10, window_seconds=60)),
):
    return await auth_service.login(db, body.email, body.password)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=10, window_seconds=60)),
):
    return await auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.logout(db, token, body.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(RateLimiter(max_requests=3, window_seconds=300)),
):
    token = await password_reset_service.forgot_password(db, body.email)
    if settings.DEBUG:
        return {"message": "Password reset link sent", "reset_token": token}
    return {"message": "Password reset link sent if account exists"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await password_reset_service.reset_password(db, body.token, body.new_password)
    return {"message": "Password reset successful"}