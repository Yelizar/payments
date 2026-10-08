from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.domain.enums import PaymentStatus
from app.workers import consumer
from app.workers.constants import MAX_PROCESS_ATTEMPTS, PAYMENTS_DLQ, PAYMENTS_RETRY_QUEUE
from app.workers.messages import PaymentCreatedEvent


@pytest.fixture
def event() -> PaymentCreatedEvent:
    return PaymentCreatedEvent(
        payment_id=uuid4(),
        idempotency_key="order-123",
        webhook_url="https://example.test/webhook",
    )


@pytest.mark.asyncio
async def test_process_payment_schedules_retry_before_max_attempts(monkeypatch, event):
    error = RuntimeError("temporary failure")
    apply_gateway = AsyncMock(side_effect=error)
    schedule_retry = AsyncMock()
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(consumer, "apply_gateway_if_pending", apply_gateway)
    monkeypatch.setattr(consumer, "schedule_retry", schedule_retry)
    monkeypatch.setattr(consumer, "move_to_dlq", move_to_dlq)

    await consumer.process_payment(event)

    schedule_retry.assert_awaited_once_with(event, error)
    move_to_dlq.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_payment_moves_final_failure_to_dlq(monkeypatch, event):
    final_event = event.model_copy(update={"attempt": MAX_PROCESS_ATTEMPTS})
    error = RuntimeError("permanent failure")
    monkeypatch.setattr(
        consumer, "apply_gateway_if_pending", AsyncMock(side_effect=error)
    )
    schedule_retry = AsyncMock()
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(consumer, "schedule_retry", schedule_retry)
    monkeypatch.setattr(consumer, "move_to_dlq", move_to_dlq)

    await consumer.process_payment(final_event)

    move_to_dlq.assert_awaited_once_with(final_event, error)
    schedule_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_retry_increments_attempt_and_publishes_expiration(monkeypatch, event):
    broker = SimpleNamespace(publish=AsyncMock())
    monkeypatch.setattr(consumer, "container", SimpleNamespace(broker=broker))

    await consumer.schedule_retry(event, RuntimeError("temporary"))

    broker.publish.assert_awaited_once()
    payload, kwargs = broker.publish.await_args.args[0], broker.publish.await_args.kwargs
    assert payload["payment_id"] == str(event.payment_id)
    assert payload["attempt"] == event.attempt + 1
    assert kwargs["routing_key"] == PAYMENTS_RETRY_QUEUE
    assert kwargs["expiration"] == 1
    assert kwargs["persist"] is True


@pytest.mark.asyncio
async def test_move_to_dlq_publishes_dead_letter_event(monkeypatch, event):
    broker = SimpleNamespace(publish=AsyncMock())
    monkeypatch.setattr(consumer, "container", SimpleNamespace(broker=broker))

    await consumer.move_to_dlq(event, consumer.PaymentNotFoundError("missing"))

    broker.publish.assert_awaited_once()
    payload, kwargs = broker.publish.await_args.args[0], broker.publish.await_args.kwargs
    assert payload["payment_id"] == str(event.payment_id)
    assert payload["attempt"] == event.attempt
    assert payload["reason"] == "missing"
    assert kwargs["routing_key"] == PAYMENTS_DLQ
    assert kwargs["persist"] is True


@pytest.mark.asyncio
async def test_send_webhook_does_nothing_without_url(event):
    event = event.model_copy(update={"webhook_url": None})

    await consumer.send_webhook(event, PaymentStatus.SUCCEEDED)

