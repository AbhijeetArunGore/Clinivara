"""
Document management REST API endpoints:
- POST /api/v1/documents
- GET /api/v1/documents/{document_id}/status
- GET /api/v1/documents/{document_id}/result
- DELETE /api/v1/documents/{document_id}
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from clinivara.api.dependencies import get_current_tenant
from clinivara.audit.audit_logger import audit_logger
from clinivara.core.errors import (
    ClinivaraError,
    DocumentNotFoundError,
    UnapprovedOutputAccessError,
    UnauthorizedAccessError,
)
from clinivara.core.security import generate_correlation_id
from clinivara.deidentification.engine import deidentification_engine
from clinivara.extraction.extractor import document_extractor
from clinivara.ingestion.stager import document_stager
from clinivara.normalization.text_cleaner import text_cleaner
from clinivara.schemas.approved_output import ApprovedDocumentOutput
from clinivara.schemas.document import (
    DocumentDeletionResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from clinivara.storage.storage_manager import storage_manager
from clinivara.validation.release_gate import release_gate

documents_router = APIRouter(prefix="/documents", tags=["Documents"])


@documents_router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Securely upload and process clinical document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF or raster image medical report"),
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Secure document intake:
    1. Validates magic bytes, file extensions, and file-size constraints.
    2. Stages document defensively into Boundary A storage.
    3. Runs extraction (with selective OCR fallback).
    4. Applies conservative clinical normalization.
    5. Performs sensitive entity detection and de-identification.
    6. Executes independent second-pass privacy validation.
    7. Evaluates release gate: APPROVED, REJECTED, or REVIEW_REQUIRED.
    """
    correlation_id = generate_correlation_id()

    try:
        content = await file.read()

        # 1. Staging into Boundary A
        document_id, staged_path, digest, page_count = document_stager.stage_upload(
            content=content,
            original_filename=file.filename or "unknown.pdf",
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        # 2. Text Extraction (with selective OCR)
        extraction_res = document_extractor.extract_document(
            tenant_id=tenant_id,
            document_id=document_id,
            correlation_id=correlation_id,
            file_path=staged_path,
        )
        raw_text = extraction_res.aggregate_text()

        # 3. Clinical Text Normalization
        cleaned_text = text_cleaner.clean_text(raw_text)

        # 4. Sensitive Entity Detection & Transformation
        deidentified_text, transformed_counts, _ = deidentification_engine.deidentify(
            text=cleaned_text,
            tenant_id=tenant_id,
            document_id=document_id,
            correlation_id=correlation_id,
        )

        # 5. Independent Privacy Validation & Release Gate Decision
        decision, warnings, _ = release_gate.evaluate_and_commit(
            tenant_id=tenant_id,
            document_id=document_id,
            correlation_id=correlation_id,
            raw_text=raw_text,
            deidentified_text=deidentified_text,
            extraction_result=extraction_res,
            transformed_counts=transformed_counts,
        )

        return DocumentUploadResponse(
            document_id=document_id,
            tenant_id=tenant_id,
            status=decision,
            sha256_digest=digest,
            received_at=datetime.now(timezone.utc).isoformat(),
            message=f"Document processed with release decision: {decision}.",
        )

    except ClinivaraError as e:
        raise e.to_http_exception(correlation_id)
    except Exception as e:
        audit_logger.record_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_type="SECURITY_ALERT",
            status="FAILURE",
            details={"error": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_PROCESSING_ERROR",
                "message": "An error occurred during secure document processing.",
                "correlation_id": correlation_id,
            },
        )


@documents_router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status and safe metadata",
)
async def get_document_status(
    document_id: str,
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Returns document processing lifecycle status.
    Enforces tenant authorization and never leaks raw clinical text.
    """
    meta = storage_manager.get_document_metadata(tenant_id, document_id)
    if not meta:
        raise DocumentNotFoundError(f"Document {document_id} not found.").to_http_exception()

    # Verify tenant ownership
    if meta.get("tenant_id") != tenant_id:
        raise UnauthorizedAccessError("Access to this document is forbidden.").to_http_exception()

    return DocumentStatusResponse(
        document_id=document_id,
        tenant_id=tenant_id,
        status=meta.get("status", "PROCESSING"),
        stage=meta.get("stage", "UNKNOWN"),
        error_code=meta.get("error_code"),
        warnings=meta.get("warnings", []),
        pages_processed=meta.get("page_count"),
        updated_at=meta.get("updated_at", datetime.now(timezone.utc).isoformat()),
    )


@documents_router.get(
    "/{document_id}/result",
    response_model=ApprovedDocumentOutput,
    summary="Retrieve verified, approved de-identified document output",
)
async def get_approved_result(
    document_id: str,
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Downstream AI consumer interface:
    Returns ONLY policy-approved, independently verified de-identified documents.
    Rejects retrieval if status is not APPROVED.
    """
    correlation_id = generate_correlation_id()

    try:
        approved_output = storage_manager.get_approved_output(tenant_id, document_id)

        # Audit downstream retrieval event
        audit_logger.record_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_type="OUTPUT_ACCESSED",
            status="SUCCESS",
            document_id=document_id,
            details={"schema_version": approved_output.schema_version},
        )

        return approved_output

    except (DocumentNotFoundError, UnapprovedOutputAccessError) as e:
        raise e.to_http_exception(correlation_id)


@documents_router.delete(
    "/{document_id}",
    response_model=DocumentDeletionResponse,
    summary="Securely delete document and associated artifacts",
)
async def delete_document(
    document_id: str,
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Deletes original files, intermediate scratch directories, and approved outputs.
    Records structured audit event.
    """
    correlation_id = generate_correlation_id()
    deleted = storage_manager.delete_document_record(tenant_id, document_id)

    if deleted:
        audit_logger.record_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_type="DOCUMENT_DELETED",
            status="SUCCESS",
            document_id=document_id,
        )
        return DocumentDeletionResponse(
            document_id=document_id,
            deleted=True,
            status="DELETED",
            message="Document and associated artifacts securely removed according to retention policy.",
        )
    else:
        return DocumentDeletionResponse(
            document_id=document_id,
            deleted=False,
            status="NOT_FOUND",
            message="Document not found or already deleted.",
        )
