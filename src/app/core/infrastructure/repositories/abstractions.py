from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.core.domain.entities.payment import Payment
from app.core.infrastructure.models.outbox import Outbox


class AbstractPaymentRepository(ABC):
    @abstractmethod
    async def get_one(self, id: UUID) -> Payment | None:
        raise NotImplementedError

    @abstractmethod
    async def get_for_update(self, id: UUID) -> Payment | None:
        raise NotImplementedError

    @abstractmethod
    async def add_one(self, payment: Payment) -> Payment:
        raise NotImplementedError

    @abstractmethod
    async def edit_one(self, payment: Payment) -> Payment | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        raise NotImplementedError


class AbstractOutboxRepository(ABC):
    @abstractmethod
    async def get_one(self, id: UUID) -> Outbox | None:
        raise NotImplementedError

    @abstractmethod
    async def add_one(self, data: dict[str, Any]) -> Outbox:
        raise NotImplementedError

    @abstractmethod
    async def get_pending_batch(self, limit: int) -> list[Outbox]:
        raise NotImplementedError

    @abstractmethod
    async def mark_published(self, event: Outbox) -> None:
        raise NotImplementedError

    @abstractmethod
    async def increase_attempts(self, event: Outbox, error: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(self, event: Outbox, error: str) -> None:
        raise NotImplementedError
