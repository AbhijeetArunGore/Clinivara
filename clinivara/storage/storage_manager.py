"""
Storage abstraction enforcing strict trust boundaries:
- Boundary A: Original clinical documents (isolated, restricted).
- Boundary B: Intermediate ephemeral artifacts and temporary OCR renders (auto-cleaned).
- Boundary C: Approved, de-identified outputs (only verified artifacts).
- Token Vault: Separately isolated longitudinal mapping.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from clinivara.core.config import settings
from clinivara.core.errors import DocumentNotFoundError, UnapprovedOutputAccessError
from clinivara.schemas.approved_output import ApprovedDocumentOutput


class StorageManager:
    """Manages segregated filesystem storage with strict trust boundary enforcement."""

    def __init__(self, storage_root: Optional[Path] = None):
        self.storage_root = storage_root or settings.storage_root
        self.boundary_a = self.storage_root / "boundary_a_raw"
        self.boundary_b = self.storage_root / "boundary_b_scratch"
        self.boundary_c = self.storage_root / "boundary_c_approved"
        self.token_vault = self.storage_root / "token_vault"
        self.meta_vault = self.storage_root / "metadata"
        self._initialize_vaults()

    def _initialize_vaults(self) -> None:
        """Create storage vault directories with restricted permissions."""
        for vault in [self.boundary_a, self.boundary_b, self.boundary_c, self.token_vault, self.meta_vault]:
            vault.mkdir(parents=True, exist_ok=True)
            try:
                # Restrict permissions where OS permits (Unix/POSIX mode 0o700)
                os.chmod(vault, 0o700)
            except Exception:
                pass

    # Boundary A: Original Documents
    def save_original_document(self, tenant_id: str, document_id: str, extension: str, content: bytes) -> Path:
        tenant_dir = self.boundary_a / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        file_path = tenant_dir / f"{document_id}{extension}"
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def get_original_document_path(self, tenant_id: str, document_id: str) -> Optional[Path]:
        tenant_dir = self.boundary_a / tenant_id
        if not tenant_dir.exists():
            return None
        matches = list(tenant_dir.glob(f"{document_id}.*"))
        return matches[0] if matches else None

    # Boundary B: Intermediate Ephemeral Artifacts
    def get_scratch_dir(self, tenant_id: str, document_id: str) -> Path:
        scratch = self.boundary_b / tenant_id / document_id
        scratch.mkdir(parents=True, exist_ok=True)
        return scratch

    def cleanup_scratch_dir(self, tenant_id: str, document_id: str) -> None:
        scratch = self.boundary_b / tenant_id / document_id
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    # Boundary C: Approved Output Storage
    def save_approved_output(self, tenant_id: str, document_id: str, output: ApprovedDocumentOutput) -> Path:
        tenant_dir = self.boundary_c / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        target_file = tenant_dir / f"{document_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(output.model_dump_json(indent=2))
        return target_file

    def get_approved_output(self, tenant_id: str, document_id: str) -> ApprovedDocumentOutput:
        target_file = self.boundary_c / tenant_id / f"{document_id}.json"
        if not target_file.exists():
            # Check if document exists in metadata to distinguish 404 from 409 unapproved
            meta = self.get_document_metadata(tenant_id, document_id)
            if meta:
                raise UnapprovedOutputAccessError(
                    f"Document {document_id} has status '{meta.get('status')}' and is not approved for retrieval."
                )
            raise DocumentNotFoundError(f"Document {document_id} not found.")

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ApprovedDocumentOutput.model_validate(data)

    # Document State & Metadata Management
    def save_document_metadata(self, tenant_id: str, document_id: str, metadata: Dict[str, Any]) -> None:
        tenant_dir = self.meta_vault / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        target_file = tenant_dir / f"{document_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def get_document_metadata(self, tenant_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        target_file = self.meta_vault / tenant_id / f"{document_id}.json"
        if not target_file.exists():
            return None
        with open(target_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Secure Deletion
    def delete_document_record(self, tenant_id: str, document_id: str) -> bool:
        """
        Delete all associated artifacts across all boundaries according to policy.
        """
        found = False

        # 1. Delete original from Boundary A
        orig = self.get_original_document_path(tenant_id, document_id)
        if orig and orig.exists():
            orig.unlink()
            found = True

        # 2. Cleanup Boundary B scratch
        self.cleanup_scratch_dir(tenant_id, document_id)

        # 3. Delete Boundary C approved output
        approved = self.boundary_c / tenant_id / f"{document_id}.json"
        if approved.exists():
            approved.unlink()
            found = True

        # 4. Delete Token vault entries
        tokens = self.token_vault / tenant_id / f"{document_id}.json"
        if tokens.exists():
            tokens.unlink()

        # 5. Delete metadata
        meta = self.meta_vault / tenant_id / f"{document_id}.json"
        if meta.exists():
            meta.unlink()
            found = True

        return found


storage_manager = StorageManager()
