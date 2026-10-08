from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.domain.entities.payment import Payment
from app.core.domain.enums import Currency, PaymentStatus
from app.core.domain.exceptions import InvalidAmountError, InvalidIdempotencyKeyError
from app.core.domain.exceptions import InvalidStatusTransitionError


def test_create_payment_has_pending_status_and_defaults(payment):
    assert payment.status is PaymentStatus.PENDING
    assert payment.payment_metadata == {"source": "test"}
    assert payment.created_at.tzinfo is not None
    assert payment.processed_at is None


def test_payment_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        Payment.create(
            amount=Decimal("0.00"),
            currency=Currency.RUB,
            idempotency_key="order-1",
        )

    with pytest.raises(InvalidAmountError):
        Payment.validate_amount(Decimal("0"))


def test_payment_rejects_blank_idempotency_key():
    with pytest.raises(InvalidIdempotencyKeyError):
        Payment.create(
            amount=Decimal("10.00"),
            currency=Currency.RUB,
            idempotency_key="   ",
        )

    with pytest.raises(InvalidIdempotencyKeyError):
        Payment.validate_idempotency_key("   ")


def test_payment_status_transition_sets_processed_at(payment):
    payment.mark_succeeded()

    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.processed_at is not None
    assert payment.processed_at.tzinfo is not None


def test_payment_cannot_be_processed_twice(payment):
    payment.mark_failed()

    with pytest.raises(InvalidStatusTransitionError):
        payment.mark_succeeded()

