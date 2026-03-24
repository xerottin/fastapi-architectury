import logging
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

import sentry_sdk
from api import router as api_router
from core.config import settings
from core.exceptions import AppException
from db.clients.mongo import MongodbServices
from db.clients.redis import RedisServices
from db.session import async_engine
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from services.check_health import _check_database, _check_redis, _check_mongodb, _check_minio, _service_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Context var for request correlation ID ───────────────────────────
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


# ── Sentry ───────────────────────────────────────────────────────────
def init_sentry() -> None:
    if settings.environment != "production":
        return
    logger.info("Environment is set to production")

    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        send_default_pii=False,
        environment=settings.environment,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[FastApiIntegration()],
    )


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")

    init_sentry()

    # Critical: database must be available
    await _check_database()

    # Non-critical: log warning and continue
    await _check_redis()
    await _check_mongodb()
    _check_minio()

    logger.info("Startup complete — services: %s", _service_status)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    logger.info("Application shutting down...")

    await async_engine.dispose()
    logger.info("Database engine disposed")

    try:
        redis = RedisServices.get_redis_client()
        await redis.aclose()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning("Redis close error: %s", e)

    try:
        await MongodbServices.close()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.warning("MongoDB close error: %s", e)

    logger.info("Shutdown complete")


# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name or "Fast-Architectury-API",
    description="Fast Architectury API",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path="/fast-arch",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
        "deepLinking": True,
        "showExtensions": True,
    },
)


# ── Middleware (order matters: outermost first) ──────────────────────

# 1. Security: Trusted hosts
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

# 2. Performance: GZip compression
app.add_middleware(GZipMiddleware, minimum_size=settings.gzip_minimum_size)

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    max_age=settings.cors_max_age,
)


# ── Request middleware ───────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log requests with ID, timing, and status."""
    # Reuse upstream request ID or generate new one
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    request_id_ctx.set(request_id)

    client_ip = request.client.host if request.client else "unknown"

    start_time = time.perf_counter()

    logger.info(
        "→ %s %s",
        request.method,
        request.url.path,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": client_ip,
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
            extra={"request_id": request_id},
        )
        raise

    process_time = time.perf_counter() - start_time

    logger.info(
        "← %s %s %s [%.2fms]",
        response.status_code,
        request.method,
        request.url.path,
        process_time * 1000,
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": round(process_time * 1000, 2),
        },
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}s"

    return response

# ── Routes ───────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Exception handlers ──────────────────────────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    rid = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "AppException: %s",
        exc.detail,
        extra={
            "request_id": rid,
            "status_code": exc.status_code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "request_id": rid},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception: %s",
        exc,
        extra={"request_id": rid},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": rid,
        },
    )
