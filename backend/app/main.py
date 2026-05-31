import logging
import subprocess
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
import app.core.slot_cache_invalidation  # noqa: F401 — register after_commit / rollback slot cache hooks
from app.core.request_context import bind_request_id, reset_request_id
from app.core.tenancy import ensure_default_tenant_exists
from app.core.rate_limit import (
    AuthenticatedWritePostRateLimitMiddleware,
    PublicEndpointRateLimitMiddleware,
    RateLimitRule,
)
from app.services.exceptions import ServiceError

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Startup/shutdown lifecycle hook.

    We intentionally "fail fast" if the database is unreachable so process supervisors (Render,
    Railway, systemd, etc.) can restart the service rather than serving partial functionality.

    This hook assumes migrations are applied before the app starts accepting traffic.
    """
    logger.info("Application startup: validating database connectivity")
    try:
        # Run pending migrations before anything else
        logger.info("Running database migrations...")
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Migrations complete")

        from app.core.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ensure_default_tenant_exists()
        logger.info("Application startup: database connectivity OK; default tenant ensured")
    except Exception:
        logger.exception("Application startup failed — full traceback above")
        raise
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="Nevase Dental - Practice Management API",
    version="1.0.0",
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


@app.get("/health")
def root_health() -> dict[str, str]:
    """Minimal health check for load balancers (e.g. Render) without API prefix."""
    return {"status": "ok"}


# CORS: MUST be first middleware, before any routes or custom middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    raw = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
    rid = str(raw).strip() if raw and str(raw).strip() else str(uuid.uuid4())
    token = bind_request_id(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        reset_request_id(token)


# Debug: Log incoming Origin header for CORS troubleshooting
@app.middleware("http")
async def debug_cors_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    logger.info(f"CORS Debug - Origin: {origin}, Method: {request.method}, Path: {request.url.path}")
    response = await call_next(request)
    # Log response CORS headers
    cors_header = response.headers.get("access-control-allow-origin")
    logger.info(f"CORS Debug - Response Access-Control-Allow-Origin: {cors_header}")
    return response


# Request timing and logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path} - Started")

    response = await call_next(request)

    # Log response
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )

    return response


# Rate limiting middleware placeholder
app.add_middleware(
    PublicEndpointRateLimitMiddleware,
    rule=RateLimitRule(window_seconds=60, max_requests=100),
)
app.add_middleware(AuthenticatedWritePostRateLimitMiddleware)


@app.exception_handler(ServiceError)
def handle_service_error(_: Request, exc: ServiceError) -> JSONResponse:
    logger.error(f"Service error: {exc.detail} (status: {exc.status_code})")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
def handle_generic_exception(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception occurred", exc_info=exc)
    # Return generic message in production to avoid leaking internal details
    # In development, we can be more verbose for debugging
    if settings.DEBUG:
        error_detail = f"Internal error: {str(exc)}"
    else:
        error_detail = "Internal server error"
    
    return JSONResponse(
        status_code=500,
        content={"detail": error_detail},
    )



app.include_router(api_router, prefix="/api/v1")
