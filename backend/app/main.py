from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.db.mongodb import close_mongo_client, get_mongo_db
from app.db.postgres import engine
from app.db.redis import close_redis, get_redis_cache
from app.logging_config import setup_logging
from app.middleware.error_handler import register_error_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up", app_name=settings.app_name, version=settings.app_version)
    yield
    logger.info("Shutting down")
    await close_mongo_client()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

register_error_handlers(app)
app.include_router(api_router)


if settings.enable_metrics:

    @app.get("/metrics")
    async def metrics():
        from prometheus_client import generate_latest
        from starlette.responses import Response

        return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/health/ready")
async def health_ready() -> JSONResponse:
    checks: dict[str, str] = {}

    # Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Check MongoDB
    try:
        db = get_mongo_db()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {e}"

    # Check Redis
    try:
        redis_client = get_redis_cache()
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())

    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            **checks,
        },
    )
