from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.register(db, body.email, body.password)


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.login(db, body.email, body.password)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    await auth_service.logout(db, body.refresh_token)
    return {"message": "Logged out successfully"}