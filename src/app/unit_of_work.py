from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core.infrastructure.repositories.abstractions import (
    AbstractOutboxRepository,
    AbstractPaymentRepository,
)
from app.core.infrastructure.repositories.outbox import OutboxRepository
from app.core.infrastructure.repositories.payment import PaymentRepository


class AbcUnitOfWork(ABC):
    payment: AbstractPaymentRepository
    outbox: AbstractOutboxRepository

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self.shutdown()

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def shutdown(self) -> None:
        raise NotImplementedError


class UnitOfWork(AbcUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.payment = PaymentRepository(self._session)
        self.outbox = OutboxRepository(self._session)
        return self

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()

    async def shutdown(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
