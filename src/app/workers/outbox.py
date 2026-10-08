import asyncio
import logging

from app.container import container
from app.unit_of_work import UnitOfWork
from app.workers.topology import declare_topology, payments_exchange

logger = logging.getLogger(__name__)


async def publish_outbox_once() -> None:
    async with UnitOfWork(container.session_factory) as uow:
        events = await uow.outbox.get_pending_batch(container.config.outbox_batch_size)
        if not events:
            return

        for event in events:
            try:
                await container.broker.publish(
                    event.payload,
                    exchange=payments_exchange,
                    routing_key=event.topic,
                    persist=True,
                )
                await uow.outbox.mark_published(event)
            except Exception as exc:
                await uow.outbox.increase_attempts(event, str(exc))
                logger.warning(
                    "Outbox publish failed, event stays pending %s",
                    event.id,
                    extra={
                        "event_id": str(event.id),
                        "topic": event.topic,
                        "attempts": event.attempts,
                        "reason": str(exc),
                    },
                )


async def run_publisher() -> None:
    async with container.broker:
        while True:
            try:
                await declare_topology(container.config.rabbitmq_url)
                await publish_outbox_once()
            except Exception:
                logger.exception("Outbox iteration failed")
            await asyncio.sleep(container.config.outbox_poll_interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_publisher())


if __name__ == "__main__":
    main()
