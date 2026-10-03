import asyncio
import hashlib
import hmac
import json
import secrets

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.exceptions import NotFoundException
from app.models.webhook import WebhookDelivery, WebhookSubscription

EVENTS = [
    "user.created",
    "user.verified",
    "user.login",
    "user.deactivated",
]


def _sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def create_subscription(db: AsyncSession, url: str, events: list[str], description: str | None = None) -> dict:
    secret = secrets.token_hex(32)
    sub = WebhookSubscription(
        url=url,
        secret=secret,
        events=",".join(events),
        description=description,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {
        "id": str(sub.id),
        "url": sub.url,
        "secret": sub.secret,
        "events": events,
        "is_active": sub.is_active,
        "description": sub.description,
        "created_at": sub.created_at.isoformat(),
    }


async def list_subscriptions(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
    )
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "url": s.url,
            "events": s.events.split(","),
            "is_active": s.is_active,
            "description": s.description,
            "created_at": s.created_at.isoformat(),
        }
        for s in subs
    ]


async def update_subscription(db: AsyncSession, sub_id: str, url: str | None = None, events: list[str] | None = None, is_active: bool | None = None, description: str | None = None) -> dict:
    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException("Webhook subscription not found")
    if url is not None:
        sub.url = url
    if events is not None:
        sub.events = ",".join(events)
    if is_active is not None:
        sub.is_active = is_active
    if description is not None:
        sub.description = description
    await db.commit()
    await db.refresh(sub)
    return {
        "id": str(sub.id),
        "url": sub.url,
        "events": sub.events.split(","),
        "is_active": sub.is_active,
        "description": sub.description,
        "created_at": sub.created_at.isoformat(),
    }


async def delete_subscription(db: AsyncSession, sub_id: str) -> None:
    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException("Webhook subscription not found")
    await db.delete(sub)
    await db.commit()


async def list_deliveries(db: AsyncSession, sub_id: str, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == sub_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    deliveries = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "event": d.event,
            "response_status": d.response_status,
            "success": d.success,
            "created_at": d.created_at.isoformat(),
        }
        for d in deliveries
    ]


async def _send_webhook(sub: WebhookSubscription, event: str, payload: dict):
    body = json.dumps(payload, default=str).encode()
    signature = _sign_payload(sub.secret, body)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                sub.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": event,
                },
            )
        status = resp.status_code
        resp_body = resp.text[:4096]
        success = 200 <= status < 300
    except Exception as e:
        status = None
        resp_body = str(e)[:4096]
        success = False

    async with async_session_maker() as db:
        delivery = WebhookDelivery(
            webhook_id=str(sub.id),
            event=event,
            request_body=body.decode(),
            response_status=status,
            response_body=resp_body,
            success=success,
        )
        db.add(delivery)
        await db.commit()


async def dispatch(event_type: str, payload: dict):
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(WebhookSubscription).where(WebhookSubscription.is_active == True)
            )
            subs = result.scalars().all()
        matching = [s for s in subs if event_type in s.events.split(",")]
        for sub in matching:
            asyncio.ensure_future(_send_webhook(sub, event_type, payload))
    except Exception:
        pass
