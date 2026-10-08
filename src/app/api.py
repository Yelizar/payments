from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.container import container
from app.core.presentation.router import payments_router
from app.security import verify_api_key
from app.settings import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await container.close()


def get_app() -> FastAPI:
    app = FastAPI(
        title="Payment service",
        docs_url="/docs",
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_enabled,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

    app.include_router(
        payments_router,
        prefix="/api/v1",
        tags=["payments"],
        dependencies=[Depends(verify_api_key)],
    )

    return app
