import aio_pika
from aio_pika import ExchangeType
from faststream.rabbit import (
    RabbitExchange,
    RabbitQueue,
)

from app.workers.constants import (
    PAYMENTS_DLQ,
    PAYMENTS_DLX,
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW_QUEUE,
    PAYMENTS_RETRY_QUEUE,
)

payments_exchange = RabbitExchange(PAYMENTS_EXCHANGE, durable=True)
payments_dlx = RabbitExchange(PAYMENTS_DLX, durable=True)

payments_new_queue = RabbitQueue(
    PAYMENTS_NEW_QUEUE,
    durable=True,
    routing_key=PAYMENTS_NEW_QUEUE,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX,
        "x-dead-letter-routing-key": PAYMENTS_DLQ,
    },
)

RETRY_QUEUE_ARGUMENTS = {
    # TTL на сообщении истекает - брокер кидает его обратно в payments.new
    "x-dead-letter-exchange": PAYMENTS_EXCHANGE,
    "x-dead-letter-routing-key": PAYMENTS_NEW_QUEUE,
}


async def declare_topology(rabbitmq_url: str) -> None:
    # объявляем очереди до первого publish, иначе outbox может упасть
    connection = await aio_pika.connect_robust(rabbitmq_url)
    try:
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            PAYMENTS_EXCHANGE,
            type=ExchangeType.DIRECT,
            durable=True,
        )
        dlx = await channel.declare_exchange(
            PAYMENTS_DLX,
            type=ExchangeType.DIRECT,
            durable=True,
        )

        new_queue = await channel.declare_queue(
            PAYMENTS_NEW_QUEUE,
            durable=True,
            arguments=payments_new_queue.arguments,
        )
        await new_queue.bind(exchange, routing_key=PAYMENTS_NEW_QUEUE)

        retry_queue = await channel.declare_queue(
            PAYMENTS_RETRY_QUEUE,
            durable=True,
            arguments=RETRY_QUEUE_ARGUMENTS,
        )
        await retry_queue.bind(exchange, routing_key=PAYMENTS_RETRY_QUEUE)

        dlq = await channel.declare_queue(PAYMENTS_DLQ, durable=True)
        await dlq.bind(dlx, routing_key=PAYMENTS_DLQ)
    finally:
        await connection.close()
