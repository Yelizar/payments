import asyncio
import logging
import random
from datetime import UTC, datetime

import aiohttp
from faststream import FastStream

from app.container import container
from app.core.domain.enums import PaymentStatus
from app.unit_of_work import UnitOfWork
from app.workers.constants import (
    MAX_PROCESS_ATTEMPTS,
    PAYMENTS_DLQ,
    PAYMENTS_RETRY_QUEUE,
    retry_delay_seconds,
)
from app.workers.messages import (
    DeadLetterEvent,
    PaymentCreatedEvent,
)
from app.workers.topology import (
    declare_topology,
    payments_dlx,
    payments_exchange,
    payments_new_queue,
)

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    pass


class PaymentNotFoundError(ProcessingError):
    pass


class GatewayDeclinedError(ProcessingError):
    """Business decline from the payment gateway. Must not be retried."""


async def emulate_payment_processing(idempotency_key: str) -> None:
    # что бы один и тот же ключ возвращал одинаковый результат
    rng = random.Random(idempotency_key)
    await asyncio.sleep(rng.uniform(2.0, 5.0))
    if rng.random() > 0.9:
        raise GatewayDeclinedError("Payment gateway emulation declined the payment")


async def apply_gateway_if_pending(event: PaymentCreatedEvent) -> PaymentStatus:
    async with UnitOfWork(container.session_factory) as uow:
        payment = await uow.payment.get_for_update(event.payment_id)
        if payment is None:
            raise PaymentNotFoundError(f"Payment not found: {event.payment_id}")
        if payment.status is not PaymentStatus.PENDING:
            return payment.status

        try:
            await emulate_payment_processing(payment.idempotency_key)
        except GatewayDeclinedError:
            payment.mark_failed()
        else:
            payment.mark_succeeded()

        await uow.payment.edit_one(payment)
        return payment.status


async def send_webhook(event: PaymentCreatedEvent, status: PaymentStatus) -> None:
    if not event.webhook_url:
        return

    payload = {
        "payment_id": str(event.payment_id),
        "status": status.value,
        "processed_at": datetime.now(UTC).isoformat(),
    }
    timeout = aiohttp.ClientTimeout(total=container.config.webhook_timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as client:
        async with client.post(event.webhook_url, json=payload) as response:
            response.raise_for_status()


async def move_to_dlq(event: PaymentCreatedEvent, exc: Exception) -> None:
    reason = str(exc)
    was_pending = False
    if not isinstance(exc, PaymentNotFoundError):
        async with UnitOfWork(container.session_factory) as uow:
            payment = await uow.payment.get_for_update(event.payment_id)
            if payment is not None and payment.status is PaymentStatus.PENDING:
                was_pending = True
                payment.mark_failed()
                await uow.payment.edit_one(payment)

        if was_pending:
            try:
                await send_webhook(event, PaymentStatus.FAILED)
            except Exception as webhook_exc:
                reason = f"{exc}; webhook failed: {webhook_exc}"
                logger.exception(
                    "Webhook failed before DLQ for payment %s",
                    event.payment_id,
                )

    dead_letter = DeadLetterEvent(
        payment_id=event.payment_id,
        webhook_url=event.webhook_url,
        attempt=event.attempt,
        reason=reason,
    )
    await container.broker.publish(
        dead_letter.model_dump(mode="json"),
        exchange=payments_dlx,
        routing_key=PAYMENTS_DLQ,
        persist=True,
    )
    logger.error(
        "Payment moved to DLQ %s; attempt=%s; reason=%s",
        event.payment_id,
        event.attempt,
        reason,
    )


async def schedule_retry(event: PaymentCreatedEvent, exc: Exception) -> None:
    retry_event = event.model_copy(update={"attempt": event.attempt + 1})
    delay = retry_delay_seconds(event.attempt)
    await container.broker.publish(
        retry_event.model_dump(mode="json"),
        exchange=payments_exchange,
        routing_key=PAYMENTS_RETRY_QUEUE,
        expiration=delay,
        persist=True,
    )
    logger.warning(
        "Payment processing will be retried %s; attempt=%s; delay=%ss; reason=%s",
        event.payment_id,
        event.attempt,
        delay,
        exc,
    )


@container.broker.subscriber(payments_new_queue, exchange=payments_exchange)
async def process_payment(event: PaymentCreatedEvent) -> None:
    try:
        payment_status = await apply_gateway_if_pending(event)
        await send_webhook(event, payment_status)
    except Exception as exc:
        if event.attempt >= MAX_PROCESS_ATTEMPTS:
            await move_to_dlq(event, exc)
            return
        await schedule_retry(event, exc)


app = FastStream(container.broker)


@app.on_startup
async def declare_payment_topology() -> None:
    await declare_topology(container.config.rabbitmq_url)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
