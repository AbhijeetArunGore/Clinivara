"""
Health check endpoints for container readiness and operational monitoring.
"""

from fastapi import APIRouter
from clinivara.core.config import settings

health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get("", summary="System Health Status")
async def health_check():
    """
    Returns high-level system operational status without disclosing
    internal infrastructure details, database strings, or storage paths.
    """
    return {
        "status": "UP",
        "service": "clinivara-document-processor",
        "version": settings.app_version,
        "environment": settings.app_env,
        "ocr_enabled": settings.ocr_enabled,
    }
