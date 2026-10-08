from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.entities.payment import Payment as DomainPayment
from app.core.infrastructure.models.payment import Payment as OrmPayment
from app.core.infrastructure.repositories.abstractions import (
    AbstractPaymentRepository,
)


class PaymentRepository(AbstractPaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(payment: OrmPayment) -> DomainPayment:
        return DomainPayment(
            id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            payment_metadata=payment.payment_metadata,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

    @staticmethod
    def _to_orm(payment: DomainPayment) -> OrmPayment:
        return OrmPayment(
            id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            payment_metadata=payment.payment_metadata,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

    async def get_one(self, id: UUID) -> DomainPayment | None:
        payment = await self.session.get(OrmPayment, id)
        return self._to_domain(payment) if payment else None

    async def get_for_update(self, id: UUID) -> DomainPayment | None:
        stmt = select(OrmPayment).where(OrmPayment.id == id).with_for_update()
        result = await self.session.execute(stmt)
        payment = result.scalar_one_or_none()
        return self._to_domain(payment) if payment else None

    async def add_one(self, payment: DomainPayment) -> DomainPayment:
        orm_payment = self._to_orm(payment)
        self.session.add(orm_payment)
        await self.session.flush()
        return payment

    async def edit_one(self, payment: DomainPayment) -> DomainPayment | None:
        orm_payment = await self.session.get(OrmPayment, payment.id)
        if orm_payment is None:
            return None

        orm_payment.amount = payment.amount
        orm_payment.currency = payment.currency
        orm_payment.description = payment.description
        orm_payment.payment_metadata = payment.payment_metadata
        orm_payment.status = payment.status
        orm_payment.idempotency_key = payment.idempotency_key
        orm_payment.webhook_url = payment.webhook_url
        orm_payment.processed_at = payment.processed_at

        await self.session.flush()
        return payment

    async def get_by_idempotency_key(
        self, idempotency_key: str
    ) -> DomainPayment | None:
        stmt = select(OrmPayment).where(OrmPayment.idempotency_key == idempotency_key)
        result = await self.session.execute(stmt)
        payment = result.scalar_one_or_none()
        return self._to_domain(payment) if payment else None
