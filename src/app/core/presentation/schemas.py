from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.domain.enums import Currency, PaymentStatus


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: Currency
    description: str | None = Field(default=None, max_length=512)
    metadata: dict[str, Any] | None = None
    webhook_url: str | None = Field(default=None, max_length=512)

    def model_post_init(self, __context: Any) -> None:
        if self.metadata is None:
            self.metadata = {}


class CreatePaymentResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime


class PaymentDetailResponse(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: PaymentStatus
    webhook_url: str | None = None
    created_at: datetime
    processed_at: datetime | None = None
