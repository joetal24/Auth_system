from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services import user as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.get_user(db, str(current_user.id))


@router.get("/", response_model=list[UserRead])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return await user_service.get_users(db, skip, limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await user_service.get_user(db, str(user_id))


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return await user_service.update_user(db, str(user_id), body)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    await user_service.deactivate_user(db, str(user_id))
    return {"message": "User deactivated"}