from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.workers import outbox


class FakeUnitOfWork:
    def __init__(self, events):
        self.outbox = AsyncMock()
        self.outbox.get_pending_batch.return_value = events
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.shutdown = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
        await self.shutdown()


@pytest.mark.asyncio
async def test_publish_outbox_marks_successful_event_published(monkeypatch):
    event = SimpleNamespace(
        id="event-1",
        payload={"payment_id": "payment-1"},
        topic="payments.new",
        attempts=0,
    )
    uow = FakeUnitOfWork([event])
    broker = SimpleNamespace(publish=AsyncMock())
    config = SimpleNamespace(outbox_batch_size=10)
    monkeypatch.setattr(outbox, "UnitOfWork", lambda _: uow)
    monkeypatch.setattr(
        outbox, "container", SimpleNamespace(session_factory=object(), broker=broker, config=config)
    )

    await outbox.publish_outbox_once()

    broker.publish.assert_awaited_once_with(
        event.payload,
        exchange=outbox.payments_exchange,
        routing_key=event.topic,
        persist=True,
    )
    uow.outbox.mark_published.assert_awaited_once_with(event)
    uow.outbox.increase_attempts.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_outbox_keeps_failed_event_pending(monkeypatch):
    event = SimpleNamespace(
        id="event-1",
        payload={"payment_id": "payment-1"},
        topic="payments.new",
        attempts=2,
    )
    error = RuntimeError("broker unavailable")
    uow = FakeUnitOfWork([event])
    broker = SimpleNamespace(publish=AsyncMock(side_effect=error))
    config = SimpleNamespace(outbox_batch_size=10)
    monkeypatch.setattr(outbox, "UnitOfWork", lambda _: uow)
    monkeypatch.setattr(
        outbox, "container", SimpleNamespace(session_factory=object(), broker=broker, config=config)
    )

    await outbox.publish_outbox_once()

    uow.outbox.increase_attempts.assert_awaited_once_with(event, str(error))
    uow.outbox.mark_published.assert_not_awaited()

