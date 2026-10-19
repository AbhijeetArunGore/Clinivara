"""
Clinivara Application Entrypoint.

Configures:
1. FastAPI application and v1 routers.
2. Security headers (HSTS, nosniff, frame denial).
3. Sanitized exception handlers preventing stack trace leakage.
4. Storage boundary initialization.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from clinivara.api.router import api_v1_router
from clinivara.core.config import settings
from clinivara.core.errors import ClinivaraError
from clinivara.storage.storage_manager import storage_manager

logger = logging.getLogger("clinivara")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown management."""
    # Ensure all storage vaults are created with proper boundary permissions
    storage_manager._initialize_vaults()
    yield
    # Graceful shutdown


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Privacy-First Clinical Document Processing Backend enforcing de-identification invariants.",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS configuration restricted to authorized frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Enforce strict defensive HTTP response headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
    return response


@app.exception_handler(ClinivaraError)
async def clinivara_exception_handler(request: Request, exc: ClinivaraError):
    """Sanitized handler for application domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.safe_details,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception sanitizer to prevent internal stack traces, system paths,
    or sensitive variables from leaking in unhandled 500 responses.
    """
    logger.error("Unhandled server exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred. Please contact the system administrator.",
            "details": {},
        },
    )


# Mount API V1 routes
app.include_router(api_v1_router)
