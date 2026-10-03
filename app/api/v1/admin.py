from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.schemas.webhook import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    WebhookSubscriptionResponse,
    WebhookDeliveryResponse,
)
from app.services import webhook as webhook_service
from app.services import audit as audit_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.post("/webhooks", response_model=WebhookSubscriptionResponse)
async def create_webhook(
    body: CreateWebhookRequest,
    db: AsyncSession = Depends(get_db),
):
    return await webhook_service.create_subscription(db, body.url, body.events, body.description)


@router.get("/webhooks", response_model=list[WebhookSubscriptionResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
):
    return await webhook_service.list_subscriptions(db)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    webhook_id: str,
    body: UpdateWebhookRequest,
    db: AsyncSession = Depends(get_db),
):
    return await webhook_service.update_subscription(
        db, webhook_id, body.url, body.events, body.is_active, body.description
    )


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
):
    await webhook_service.delete_subscription(db, webhook_id)
    return {"message": "Webhook deleted"}


@router.get("/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await webhook_service.list_deliveries(db, webhook_id)


@router.get("/audit-logs")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id: str | None = None,
    action: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await audit_service.get_logs(db, skip, limit, user_id, action)
