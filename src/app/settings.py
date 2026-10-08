from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class DataBaseSettings(BaseSettings):
    echo: bool = False
    pg_db: str
    pg_user: str
    pg_password: str
    pg_host: str
    pg_port: int

    def get_url(self) -> str:
        url = f"postgresql+asyncpg://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="allow",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers_count: int = 1
    reload: bool = False
    debug: bool = False

    # CORS
    cors_enabled: bool = True
    cors_origins: List[str] = [
        "http://localhost:8000",
    ]
    cors_methods: List[str] = [
        "GET",
        "POST",
    ]
    cors_headers: List[str] = [
        "Content-Type",
        "X-API-Key",
        "Idempotency-Key",
    ]

    # Outbox worker
    outbox_batch_size: int = 100
    outbox_poll_interval_seconds: float = 1.0

    # Webhook delivery
    webhook_timeout_seconds: float = 5.0

    api_key: str
    rabbitmq_url: str

    db: DataBaseSettings


settings = Settings()  # type: ignore[call-arg]
