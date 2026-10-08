from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.core.domain.enums import Currency, PaymentStatus
from app.core.domain.exceptions import (
    InvalidAmountError,
    InvalidIdempotencyKeyError,
    InvalidStatusTransitionError,
)


class Payment(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: Currency
    description: str | None = Field(default=None, max_length=512)
    payment_metadata: dict = Field(default_factory=dict)
    status: PaymentStatus = PaymentStatus.PENDING
    idempotency_key: str = Field(min_length=1, max_length=64)
    webhook_url: str | None = Field(default=None, max_length=512)
    created_at: datetime
    processed_at: datetime | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise InvalidAmountError("Payment amount must be positive")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        if not value.strip() or len(value) > 64:
            raise InvalidIdempotencyKeyError(
                "Idempotency key must contain 1 to 64 non-whitespace characters"
            )
        return value

    @classmethod
    def create(
        cls,
        *,
        amount: Decimal,
        currency: Currency,
        idempotency_key: str,
        description: str | None = None,
        payment_metadata: dict | None = None,
        webhook_url: str | None = None,
    ) -> "Payment":
        return cls(
            id=uuid4(),
            amount=amount,
            currency=currency,
            description=description,
            payment_metadata=payment_metadata or {},
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            webhook_url=webhook_url,
            created_at=datetime.now(UTC),
        )

    def mark_succeeded(self) -> None:
        self._mark_status(PaymentStatus.SUCCEEDED)

    def mark_failed(self) -> None:
        self._mark_status(PaymentStatus.FAILED)

    def _mark_status(self, status: PaymentStatus) -> None:
        if self.status is not PaymentStatus.PENDING:
            raise InvalidStatusTransitionError(
                f"Cannot transition payment {self.id} from {self.status} to {status}"
            )
        self.status = status
        self.processed_at = datetime.now(UTC)
