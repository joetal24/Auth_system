from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundException
from app.models.session import Session


async def get_user_sessions(db: AsyncSession, user_id: str, current_session_id: str) -> list[dict]:
    result = await db.execute(
        select(Session).where(Session.user_id == user_id, Session.is_revoked == False)
    )
    return [
        {
            "id": str(s.id),
            "device_info": s.device_info,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "is_current": str(s.id) == current_session_id,
        }
        for s in result.scalars().all()
    ]


async def revoke_session_by_id(db: AsyncSession, session_id: str, user_id: str) -> None:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.is_revoked:
        raise NotFoundException("Session not found")
    session.is_revoked = True
    await db.commit()


async def revoke_other_sessions(db: AsyncSession, current_session_id: str, user_id: str) -> None:
    result = await db.execute(
        select(Session).where(Session.user_id == user_id, Session.is_revoked == False)
    )
    for s in result.scalars().all():
        if str(s.id) != current_session_id:
            s.is_revoked = True
    await db.commit()
