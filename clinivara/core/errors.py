"""
Secure error hierarchy and sanitization.

Ensures no internal filesystem paths, stack traces, patient identifiers,
or sensitive clinical snippets are exposed to clients.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class ClinivaraError(Exception):
    """Base exception for all Clinivara operations."""

    def __init__(
        self,
        message: str,
        error_code: str = "PROCESSING_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        safe_details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.safe_details = safe_details or {}

    def to_http_exception(self, correlation_id: Optional[str] = None) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail={
                "error_code": self.error_code,
                "message": self.message,
                "correlation_id": correlation_id or "unknown",
            },
        )


class InvalidDocumentError(ClinivaraError):
    """Document format, signature, or extension validation failure."""

    def __init__(self, message: str = "Invalid or corrupted document provided."):
        super().__init__(
            message=message,
            error_code="INVALID_DOCUMENT",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class SecurityViolationError(ClinivaraError):
    """Security limit or invariant violation (e.g. decompression bomb, path traversal)."""

    def __init__(self, message: str = "Document rejected due to security policy violation."):
        super().__init__(
            message=message,
            error_code="SECURITY_VIOLATION",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DocumentTooLargeError(SecurityViolationError):
    def __init__(self, message: str = "Document exceeds allowable size limits."):
        super().__init__(message=message)
        self.error_code = "DOCUMENT_TOO_LARGE"
        self.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


class ExtractionError(ClinivaraError):
    """Failure during text or OCR extraction."""

    def __init__(self, message: str = "Document text extraction failed."):
        super().__init__(
            message=message,
            error_code="EXTRACTION_FAILURE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class PrivacyValidationError(ClinivaraError):
    """Failure during independent second-pass privacy validation."""

    def __init__(self, message: str = "Document output failed privacy verification."):
        super().__init__(
            message=message,
            error_code="PRIVACY_VALIDATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class DocumentNotFoundError(ClinivaraError):
    """Requested document ID does not exist."""

    def __init__(self, message: str = "Document not found."):
        super().__init__(
            message=message,
            error_code="DOCUMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedAccessError(ClinivaraError):
    """Access denied for the requested document or tenant."""

    def __init__(self, message: str = "Access to requested document is unauthorized."):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class UnapprovedOutputAccessError(ClinivaraError):
    """Attempted retrieval of an output that has not achieved APPROVED status."""

    def __init__(self, message: str = "Document is not approved for downstream retrieval."):
        super().__init__(
            message=message,
            error_code="OUTPUT_NOT_APPROVED",
            status_code=status.HTTP_409_CONFLICT,
        )
