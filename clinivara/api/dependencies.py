"""
FastAPI dependency injection for authentication and tenant isolation.
"""

from typing import Optional
from fastapi import Header, HTTPException, status

from clinivara.core.config import settings
from clinivara.core.errors import UnauthorizedAccessError
from clinivara.core.security import verify_api_key


async def get_current_tenant(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Authenticate request via X-API-Key header using constant-time verification.
    Returns the associated tenant identifier for row- and storage-level data isolation.
    """
    try:
        tenant_id = verify_api_key(x_api_key)
        return tenant_id
    except UnauthorizedAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": str(e)},
        )
