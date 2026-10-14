"""
Secure staging pipeline for untrusted document uploads into Boundary A.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from clinivara.audit.audit_logger import audit_logger
from clinivara.core.errors import InvalidDocumentError
from clinivara.core.security import (
    calculate_sha256_digest,
    generate_document_id,
    sanitize_filename,
)
from clinivara.ingestion.validator import (
    inspect_image_safety,
    inspect_pdf_preliminary,
    validate_file_size_and_signature,
)
from clinivara.storage.storage_manager import storage_manager


class DocumentStager:
    """Safely validates and stages incoming documents into isolated Boundary A storage."""

    @staticmethod
    def stage_upload(
        content: bytes,
        original_filename: str,
        tenant_id: str,
        correlation_id: str,
    ) -> Tuple[str, Path, str, int]:
        """
        Validates untrusted upload and commits it to Boundary A.
        Returns (document_id, staged_file_path, sha256_digest, page_count).
        """
        # 1. Filename sanitization
        safe_orig_name = sanitize_filename(original_filename)

        # 2. Size and signature validation
        format_name, canonical_ext = validate_file_size_and_signature(content)

        # 3. Format-specific defensive inspection
        if format_name in ("png", "jpeg"):
            inspect_image_safety(content)
            page_count = 1

        # 4. Generate random document ID
        document_id = generate_document_id()

        # 5. Save to isolated Boundary A
        staged_path = storage_manager.save_original_document(
            tenant_id=tenant_id,
            document_id=document_id,
            extension=canonical_ext,
            content=content,
        )

        # 6. PDF deep inspection after saving
        if format_name == "pdf":
            try:
                page_count = inspect_pdf_preliminary(staged_path)
            except Exception:
                # If preliminary check fails, delete staged file immediately
                if staged_path.exists():
                    staged_path.unlink()
                raise

        # 7. Calculate SHA-256 digest
        digest = calculate_sha256_digest(staged_path)

        # 8. Record initial metadata
        initial_meta = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "sanitized_original_filename": safe_orig_name,
            "format": format_name,
            "extension": canonical_ext,
            "page_count": page_count,
            "sha256_digest": digest,
            "status": "STAGED",
            "stage": "INGESTION_COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        storage_manager.save_document_metadata(tenant_id, document_id, initial_meta)

        # 9. Audit event
        audit_logger.record_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_type="DOCUMENT_UPLOADED",
            status="SUCCESS",
            document_id=document_id,
            details={
                "format": format_name,
                "page_count": page_count,
                "sha256": digest,
            },
        )

        return document_id, staged_path, digest, page_count


document_stager = DocumentStager()
