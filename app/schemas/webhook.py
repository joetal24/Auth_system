from pydantic import BaseModel, field_validator

from app.services.webhook import EVENTS


class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str]
    description: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if e not in EVENTS]
        if invalid:
            raise ValueError(f"Invalid events: {', '.join(invalid)}. Valid: {', '.join(EVENTS)}")
        return v


class UpdateWebhookRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    description: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            invalid = [e for e in v if e not in EVENTS]
            if invalid:
                raise ValueError(f"Invalid events: {', '.join(invalid)}. Valid: {', '.join(EVENTS)}")
        return v


class WebhookSubscriptionResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    description: str | None
    created_at: str


class WebhookDeliveryResponse(BaseModel):
    id: str
    event: str
    response_status: int | None
    success: bool
    created_at: str
