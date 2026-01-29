"""FastAPI application entrypoint."""

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import init_db, check_db_health
from app.temporal.client import get_temporal_client, close_temporal_client
from app.config.logging import setup_logging, get_logger
from app.config.rate_limit import setup_rate_limiting
from app.api import router as tasks_router
from app.core.schemas import ErrorResponse

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Application startup")
    init_db()
    logger.info("Database initialized")

    # Test Temporal connection
    try:
        await get_temporal_client()
        logger.info("Temporal client initialized")
    except Exception as e:
        logger.warning(
            "Temporal client initialization failed (will retry on first use)",
            extra={"error": str(e)},
        )

    yield

    # Shutdown
    logger.info("Application shutdown")
    await close_temporal_client()
    logger.info("Temporal client closed")


# Create FastAPI app
app = FastAPI(
    title="Quantum Circuit Execution API",
    description="Asynchronous quantum circuit execution system using Temporal",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting
setup_rate_limiting(app)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for correlation."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(exc),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred.",
            detail=str(exc),
        ).model_dump(),
    )


# Health check endpoint (no rate limiting)
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    Checks database and Temporal Server connectivity.
    """
    db_healthy = check_db_health()

    temporal_healthy = False
    try:
        client = await get_temporal_client()
        temporal_healthy = True
    except Exception:
        pass

    if db_healthy and temporal_healthy:
        return {"status": "healthy", "database": "ok", "temporal": "ok"}
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "ok" if db_healthy else "error",
                "temporal": "ok" if temporal_healthy else "error",
            },
        )


# Include routers
app.include_router(tasks_router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Quantum Circuit Execution API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
