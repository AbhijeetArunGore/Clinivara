"""
API router registering all v1 endpoints.
"""

from fastapi import APIRouter
from clinivara.api.ai import ai_router
from clinivara.api.documents import documents_router
from clinivara.api.health import health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(documents_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(ai_router)
