from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentCreatedEvent(BaseModel):
    payment_id: UUID
    idempotency_key: str
    webhook_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    attempt: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DeadLetterEvent(BaseModel):
    payment_id: UUID
    webhook_url: str | None = None
    attempt: int
    reason: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)
