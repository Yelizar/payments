import uvicorn

from app.settings import settings


def main():
    uvicorn.run(
        "app.api:get_app",
        factory=True,
        reload=settings.reload,
        host=settings.host,
        port=settings.port,
        workers=settings.workers_count,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
