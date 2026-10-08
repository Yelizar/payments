from fastapi import (
    HTTPException,
    Security,
    status,
)
from fastapi.security.api_key import APIKeyHeader

from app.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(key: str = Security(api_key_header)) -> str:
    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid or missing API key",
        )
    return key
