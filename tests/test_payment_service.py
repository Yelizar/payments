from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.application.services.payment import (
    PaymentNotFoundException,
    PaymentService,
)
from app.core.domain.entities.payment import Payment
from app.core.domain.enums import Currency, PaymentStatus
from app.core.presentation.schemas import CreatePaymentRequest
from app.workers.constants import PAYMENTS_NEW_QUEUE
from app.core.infrastructure.models.outbox import OutboxStatus


class FakeUnitOfWork:
    def __init__(self, payment_repository, outbox_repository):
        self.payment = payment_repository
        self.outbox = outbox_repository
        self.rollback = AsyncMock()
        self.commit = AsyncMock()
        self.shutdown = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
        await self.shutdown()


@pytest.fixture
def create_request() -> CreatePaymentRequest:
    return CreatePaymentRequest(
        amount=Decimal("100.00"),
        currency=Currency.RUB,
        description="Order payment",
        metadata={"order_id": "order-123"},
        webhook_url="https://example.test/webhook",
    )


@pytest.mark.asyncio
async def test_create_payment_writes_payment_and_outbox(create_request):
    payment_repository = AsyncMock()
    outbox_repository = AsyncMock()
    payment_repository.add_one.side_effect = lambda payment: payment
    uow = FakeUnitOfWork(payment_repository, outbox_repository)

    response = await PaymentService(uow).create_payment(create_request, "order-123")

    payment = payment_repository.add_one.await_args.args[0]
    event = outbox_repository.add_one.await_args.args[0]

    assert response.payment_id == payment.id
    assert response.status is PaymentStatus.PENDING
    assert event["topic"] == PAYMENTS_NEW_QUEUE
    assert event["payload"]["payment_id"] == str(payment.id)
    assert event["payload"]["idempotency_key"] == "order-123"
    assert event["status"] is OutboxStatus.PENDING
    uow.commit.assert_awaited_once()
    uow.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_payment_returns_existing_payment_after_duplicate_key(
    create_request,
):
    existing_payment = Payment.create(
        amount=Decimal("100.00"),
        currency=Currency.RUB,
        idempotency_key="order-123",
    )
    payment_repository = AsyncMock()
    payment_repository.add_one.side_effect = IntegrityError(
        "insert", {}, Exception("duplicate key")
    )
    payment_repository.get_by_idempotency_key.return_value = existing_payment
    uow = FakeUnitOfWork(payment_repository, AsyncMock())

    response = await PaymentService(uow).create_payment(create_request, "order-123")

    assert response.payment_id == existing_payment.id
    assert response.status is PaymentStatus.PENDING
    uow.rollback.assert_awaited_once()
    payment_repository.get_by_idempotency_key.assert_awaited_once_with("order-123")


@pytest.mark.asyncio
async def test_get_payment_raises_for_unknown_payment():
    payment_repository = AsyncMock()
    payment_repository.get_one.return_value = None
    uow = FakeUnitOfWork(payment_repository, AsyncMock())

    with pytest.raises(PaymentNotFoundException):
        await PaymentService(uow).get_payment(uuid4())

    uow.rollback.assert_awaited_once()


