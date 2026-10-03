from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log(db: AsyncSession, user_id: str | None, action: str, details: dict | None = None) -> None:
    import json
    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=json.dumps(details) if details else None,
    )
    db.add(entry)
    await db.commit()


async def get_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_id: str | None = None,
    action: str | None = None,
) -> list[dict]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "user_id": l.user_id,
            "action": l.action,
            "details": l.details,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
