"""
Structured, privacy-preserving audit schemas.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditEvent(BaseModel):
    """
    Immutable structured audit event.
    Guaranteed not to contain sensitive personal identifiers or raw clinical text.
    """
    model_config = ConfigDict(frozen=True)

    event_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tenant_id: str
    document_id: Optional[str] = None
    correlation_id: str
    event_type: Literal[
        "DOCUMENT_UPLOADED",
        "EXTRACTION_COMPLETED",
        "EXTRACTION_FAILED",
        "NORMALIZATION_COMPLETED",
        "DEIDENTIFICATION_COMPLETED",
        "PRIVACY_VALIDATION_PASSED",
        "PRIVACY_VALIDATION_FAILED",
        "RELEASE_APPROVED",
        "RELEASE_REJECTED",
        "RELEASE_REVIEW_REQUIRED",
        "OUTPUT_ACCESSED",
        "DOCUMENT_DELETED",
        "SECURITY_ALERT",
    ]
    status: Literal["SUCCESS", "FAILURE", "WARNING"]
    details: Dict[str, Any] = Field(default_factory=dict)
