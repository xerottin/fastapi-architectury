from fastapi import APIRouter
from sqlalchemy import text
from starlette.responses import JSONResponse

from core.config import settings
from db.clients.mongo import MongodbServices
from db.clients.redis import RedisServices
from db.session import async_session

router = APIRouter()


# ── Debug routes ─────────────────────────────────────────────────────
if settings.debug:

    @router.get("/sentry-debug")
    async def trigger_error():
        1 / 0



@router.get("")
async def health_check():
    """Liveness probe — app is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check(_service_status=None):
    """Readiness probe — checks all dependencies."""
    checks: dict[str, str] = {}

    # Database
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # Redis
    try:
        redis = RedisServices.get_redis_client()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    # MongoDB
    try:
        client = MongodbServices.get_client()
        await client.admin.command("ping")
        checks["mongodb"] = "ok"
    except Exception:
        checks["mongodb"] = "unavailable"

    # MinIO
    checks["minio"] = "ok" if _service_status["minio"] else "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if all_ok else "degraded", "checks": checks},
    )

