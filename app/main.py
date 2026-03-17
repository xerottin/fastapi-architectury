import logging
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

import sentry_sdk
from api import router as api_router
from core.config import settings
from core.dependencies import get_minio_service
from core.exceptions import AppException
from db.session import async_session
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sqlalchemy import text


logger = logging.getLogger(__name__)

# ── Context var for request correlation ID ───────────────────────────
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


# ── Sentry ───────────────────────────────────────────────────────────
def init_sentry() -> None:
    if settings.environment != "production":
        return

    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        send_default_pii=True,
        environment=settings.environment,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[FastApiIntegration()],
    )


# ── Service readiness flags (graceful degradation) ───────────────────
_service_status: dict[str, bool] = {
    "database": True,
    "minio": False,
    "mongodb": False,
    "redis": False,
}


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    init_sentry()
    logger.info("Sentry initialized")

    try:
        async with async_session.begin() as conn:
            await conn.execute(text("SELECT 1"))
        _service_status["database"] = True
        logger.info("Database connection OK")
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        raise

    try:
        minio_client = get_minio_service()
        # MinioService.init_bucket(
        #     minio_client,
        #     settings.minio_bucket,
        #     auto_public=True,
        # )
        _service_status["minio"] = True
        logger.info("MinIO buckets ready")
    except Exception as e:
        _service_status["minio"] = False
        logger.warning("MinIO startup failed (degraded mode): %s", e)
    yield


# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name or "Zehn-Architectury-API",
    description="Zehn Architectury API",
    root_path="/fast-arch",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    version=settings.app_version,
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        # "docExpansion": "none",   # none | list | full
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
        # "filter": True,
        "deepLinking": True,
        "showExtensions": True,

    }
    # docs_url="/docs" if settings.debug else None,
    # redoc_url="/redoc" if settings.debug else None,
    # openapi_url="/openapi.json" if settings.debug else None,
)


# ── Middleware (order matters: outermost first) ──────────────────────

# 1. Security: Trusted hosts (защита от Host header injection)
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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    max_age=settings.cors_max_age,
)


# ── Request middleware ───────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log requests with ID, timing, status, and rate limiting."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request_id_ctx.set(request_id)

    client_ip = request.client.host if request.client else "unknown"


    start_time = time.perf_counter()

    # Log incoming request
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

    # Log response
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

    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}s"

    return response

# ── Health / Readiness ───────────────────────────────────────────────
@app.get("/health", tags=["infra"])
async def health_check():
    """Liveness probe — app is running."""
    return {"status": "okay_1"}


@app.get("/ready", tags=["infra"])
async def readiness_check():
    """Readiness probe — checks all dependencies."""
    checks: dict[str, str] = {}

    # Database
    try:
        async with async_session.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # MinIO
    checks["minio"] = "ok" if _service_status["minio"] else "unavailable"



# ── Debug routes ─────────────────────────────────────────────────────
if settings.debug:

    @app.get("/sentry-debug", tags=["infra"])
    async def trigger_error():
        1 / 0

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