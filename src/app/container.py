from faststream.rabbit import Channel, RabbitBroker
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.core.application.services.payment import PaymentService
from app.settings import Settings, settings
from app.unit_of_work import UnitOfWork


class Container:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self.broker: RabbitBroker = RabbitBroker(
            config.rabbitmq_url,
            default_channel=Channel(
                publisher_confirms=True,
                on_return_raises=True,
            ),
        )
        self.engine: AsyncEngine = create_async_engine(
            config.db.get_url(),
            echo=config.db.echo,
            pool_pre_ping=True,
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def get_uow(self) -> UnitOfWork:
        return UnitOfWork(session_factory=self.session_factory)

    def get_payment_service(self) -> PaymentService:
        return PaymentService(uow=self.get_uow())

    async def close(self) -> None:
        await self.engine.dispose()


container = Container(settings)
