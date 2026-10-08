from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.models.outbox import Outbox, OutboxStatus
from app.core.infrastructure.repositories.abstractions import (
    AbstractOutboxRepository,
)


class OutboxRepository(AbstractOutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_one(self, id: UUID) -> Outbox | None:
        return await self.session.get(Outbox, id)

    async def add_one(self, data: dict[str, Any]) -> Outbox:
        event = Outbox(**data)
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_pending_batch(self, limit: int) -> list[Outbox]:
        stmt: Select = (
            select(Outbox)
            .where(Outbox.status == OutboxStatus.PENDING)
            .order_by(Outbox.created_at.asc())
            .limit(limit)
            # два воркера не должны взять одну и ту же запись
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_published(self, event: Outbox) -> None:
        event.status = OutboxStatus.PUBLISHED
        event.published_at = datetime.now(UTC)
        event.last_error = None
        await self.session.flush()

    async def increase_attempts(self, event: Outbox, error: str) -> None:
        event.attempts += 1
        event.last_error = error[:2000]
        await self.session.flush()

    async def mark_failed(self, event: Outbox, error: str) -> None:
        event.status = OutboxStatus.FAILED
        event.last_error = error[:2000]
        await self.session.flush()
