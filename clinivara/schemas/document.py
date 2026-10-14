"""
Pydantic models for API request/response lifecycles.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    """Initial response returned upon document upload and staging."""
    model_config = ConfigDict(frozen=True)

    document_id: str
    tenant_id: str
    status: Literal["STAGED", "PROCESSING", "APPROVED", "REJECTED", "REVIEW_REQUIRED"]
    sha256_digest: str
    received_at: str
    message: str = "Document securely accepted for processing."


class DocumentStatusResponse(BaseModel):
    """Safe processing status response without leaking raw content."""
    model_config = ConfigDict(frozen=True)

    document_id: str
    tenant_id: str
    status: Literal["STAGED", "PROCESSING", "APPROVED", "REJECTED", "REVIEW_REQUIRED"]
    stage: str
    error_code: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    pages_processed: Optional[int] = None
    updated_at: str


class DocumentDeletionResponse(BaseModel):
    """Response returned upon secure deletion request."""
    model_config = ConfigDict(frozen=True)

    document_id: str
    deleted: bool
    status: Literal["DELETED", "NOT_FOUND"]
    message: str
