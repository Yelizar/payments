from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.domain.entities.payment import Payment
from app.core.domain.exceptions import BaseException
from app.core.infrastructure.models.outbox import OutboxStatus
from app.core.presentation.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetailResponse,
)
from app.unit_of_work import AbcUnitOfWork
from app.workers.constants import PAYMENTS_NEW_QUEUE


class PaymentService:
    def __init__(self, uow: AbcUnitOfWork):
        self.uow = uow

    async def create_payment(
        self,
        request: CreatePaymentRequest,
        idempotency_key: str,
    ) -> CreatePaymentResponse:
        async with self.uow:
            try:
                payment = Payment.create(
                    amount=request.amount,
                    currency=request.currency,
                    description=request.description,
                    payment_metadata=request.metadata,
                    webhook_url=request.webhook_url,
                    idempotency_key=idempotency_key,
                )
                payment = await self.uow.payment.add_one(payment)

                await self.uow.outbox.add_one(
                    {
                        "topic": PAYMENTS_NEW_QUEUE,
                        "payload": {
                            "payment_id": str(payment.id),
                            "idempotency_key": payment.idempotency_key,
                            "webhook_url": payment.webhook_url,
                        },
                        "status": OutboxStatus.PENDING,
                    }
                )
            except IntegrityError:
                await self.uow.rollback()

                payment = await self.uow.payment.get_by_idempotency_key(
                    idempotency_key
                )
                if not payment:
                    raise PaymentServiceException(
                        f"Unexpected integrity error for idempotency key: {idempotency_key}"
                    )

        return CreatePaymentResponse(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )

    async def get_payment(self, payment_id: UUID) -> PaymentDetailResponse:
        async with self.uow:
            payment = await self.uow.payment.get_one(payment_id)
            if not payment:
                raise PaymentNotFoundException(f"Payment not found: {payment_id}")

        return PaymentDetailResponse(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=payment.payment_metadata or {},
            status=payment.status,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )


class PaymentServiceException(BaseException):
    pass


class PaymentNotFoundException(PaymentServiceException):
    pass
