import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.domain.enums import Currency, PaymentStatus
from app.core.infrastructure.models.base import Base


class Payment(Base):

    __tablename__ = "payments"

    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency_enum"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    payment_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    webhook_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
