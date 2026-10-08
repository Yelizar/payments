from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.domain.entities.payment import Payment
from app.core.domain.enums import Currency


@pytest.fixture
def payment() -> Payment:
    return Payment.create(
        amount=Decimal("100.00"),
        currency=Currency.RUB,
        idempotency_key="order-123",
        description="Test payment",
        payment_metadata={"source": "test"},
        webhook_url="https://example.test/webhook",
    )


@pytest.fixture
def payment_id():
    return uuid4()


@pytest.fixture
def created_at() -> datetime:
    return datetime.now(UTC)

