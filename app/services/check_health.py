import logging

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from sqlalchemy import text

from core.dependencies import get_minio_service
from db.clients.mongo import MongodbServices
from db.clients.redis import RedisServices
from db.session import async_session



logger = logging.getLogger(__name__)
# ── Service readiness flags (graceful degradation) ───────────────────
_service_status: dict[str, bool] = {
    "database": True,
    "minio": True,
    "mongodb": True,
    "redis": True,
}

# ── Startup health checks ───────────────────────────────────────────
async def _check_database() -> None:
    """Check database connection (critical — app cannot start without it)."""
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    _service_status["database"] = True
    logger.info("Database connection OK")


async def _check_redis() -> None:
    """Check Redis connection (non-critical)."""
    try:
        redis = RedisServices.get_redis_client()
        await redis.ping()
        _service_status["redis"] = True

        FastAPICache.init(
            RedisBackend(redis),
            prefix="fastapi-cache"
        )

        logger.info("Redis connection OK")
    except Exception as e:
        _service_status["redis"] = False
        logger.warning("Redis unavailable (degraded mode): %s", e)


async def _check_mongodb() -> None:
    """Check MongoDB connection (non-critical)."""
    try:
        client = MongodbServices.get_client()
        await client.admin.command("ping")
        _service_status["mongodb"] = True
        logger.info("MongoDB connection OK")
    except Exception as e:
        _service_status["mongodb"] = False
        logger.warning("MongoDB unavailable (degraded mode): %s", e)


def _check_minio() -> None:
    """Check MinIO connection (non-critical)."""
    try:
        get_minio_service()
        _service_status["minio"] = True
        logger.info("MinIO buckets ready")
    except Exception as e:
        _service_status["minio"] = False
        logger.warning("MinIO unavailable (degraded mode): %s", e)

