"""
Storage abstraction enforcing strict trust boundaries:
- Boundary A: Original clinical documents (isolated, restricted).
- Boundary B: Intermediate ephemeral artifacts and temporary OCR renders (auto-cleaned).
- Boundary C: Approved, de-identified outputs (only verified artifacts).
- Token Vault: Separately isolated longitudinal mapping.
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from clinivara.core.config import settings
from clinivara.core.errors import (
    DocumentNotFoundError,
    SecurityViolationError,
    UnapprovedOutputAccessError,
)
from clinivara.schemas.approved_output import ApprovedDocumentOutput

VALID_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")
VALID_EXT_PATTERN = re.compile(r"^\.[a-zA-Z0-9]+$")


class StorageManager:
    """Manages segregated filesystem storage with strict trust boundary enforcement."""

    def __init__(self, storage_root: Path | None = None):
        self.storage_root = (storage_root or settings.storage_root).resolve()
        self.boundary_a = self.storage_root / "boundary_a_raw"
        self.boundary_b = self.storage_root / "boundary_b_scratch"
        self.boundary_c = self.storage_root / "boundary_c_approved"
        self.token_vault = self.storage_root / "token_vault"
        self.meta_vault = self.storage_root / "metadata"
        self._initialize_vaults()

    def _validate_id(self, identifier: str, name: str) -> None:
        """Validate identifier contains only safe alphanumeric, underscore, or hyphen characters."""
        if not identifier or not VALID_ID_PATTERN.match(identifier):
            raise SecurityViolationError(f"Invalid {name} format: potential path traversal detected.")

    def _ensure_within_vault(self, path: Path, vault_root: Path) -> Path:
        """Verify that resolved target path does not escape designated vault root."""
        resolved_path = path.resolve()
        resolved_vault = vault_root.resolve()
        if not resolved_path.is_relative_to(resolved_vault):
            raise SecurityViolationError(f"Path traversal violation: {path} escapes vault {vault_root}")
        return resolved_path

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
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        if not VALID_EXT_PATTERN.match(extension):
            raise SecurityViolationError("Invalid file extension format.")

        tenant_dir = self.boundary_a / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._ensure_within_vault(tenant_dir / f"{document_id}{extension}", self.boundary_a)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def get_original_document_path(self, tenant_id: str, document_id: str) -> Path | None:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        tenant_dir = self._ensure_within_vault(self.boundary_a / tenant_id, self.boundary_a)
        if not tenant_dir.exists():
            return None
        matches = list(tenant_dir.glob(f"{document_id}.*"))
        return matches[0] if matches else None

    # Boundary B: Intermediate Ephemeral Artifacts
    def get_scratch_dir(self, tenant_id: str, document_id: str) -> Path:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        scratch = self._ensure_within_vault(self.boundary_b / tenant_id / document_id, self.boundary_b)
        scratch.mkdir(parents=True, exist_ok=True)
        return scratch

    def cleanup_scratch_dir(self, tenant_id: str, document_id: str) -> None:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        scratch = self._ensure_within_vault(self.boundary_b / tenant_id / document_id, self.boundary_b)
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    # Boundary C: Approved Output Storage
    def save_approved_output(self, tenant_id: str, document_id: str, output: ApprovedDocumentOutput) -> Path:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        tenant_dir = self.boundary_c / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        target_file = self._ensure_within_vault(tenant_dir / f"{document_id}.json", self.boundary_c)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(output.model_dump_json(indent=2))
        return target_file

    def get_approved_output(self, tenant_id: str, document_id: str) -> ApprovedDocumentOutput:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        target_file = self._ensure_within_vault(self.boundary_c / tenant_id / f"{document_id}.json", self.boundary_c)
        if not target_file.exists():
            # Check if document exists in metadata to distinguish 404 from 409 unapproved
            meta = self.get_document_metadata(tenant_id, document_id)
            if meta:
                raise UnapprovedOutputAccessError(
                    f"Document {document_id} has status '{meta.get('status')}' and is not approved for retrieval."
                )
            raise DocumentNotFoundError(f"Document {document_id} not found.")

        with open(target_file, encoding="utf-8") as f:
            data = json.load(f)
        return ApprovedDocumentOutput.model_validate(data)

    # Document State & Metadata Management
    def save_document_metadata(self, tenant_id: str, document_id: str, metadata: dict[str, Any]) -> None:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        tenant_dir = self.meta_vault / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        target_file = self._ensure_within_vault(tenant_dir / f"{document_id}.json", self.meta_vault)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def get_document_metadata(self, tenant_id: str, document_id: str) -> dict[str, Any] | None:
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        target_file = self._ensure_within_vault(self.meta_vault / tenant_id / f"{document_id}.json", self.meta_vault)
        if not target_file.exists():
            return None
        with open(target_file, encoding="utf-8") as f:
            return json.load(f)

    # Secure Deletion
    def delete_document_record(self, tenant_id: str, document_id: str) -> bool:
        """
        Delete all associated artifacts across all boundaries according to policy.
        """
        self._validate_id(tenant_id, "tenant_id")
        self._validate_id(document_id, "document_id")
        found = False

        # 1. Delete original from Boundary A
        orig = self.get_original_document_path(tenant_id, document_id)
        if orig and orig.exists():
            orig.unlink()
            found = True

        # 2. Cleanup Boundary B scratch
        self.cleanup_scratch_dir(tenant_id, document_id)

        # 3. Delete Boundary C approved output
        approved = self._ensure_within_vault(self.boundary_c / tenant_id / f"{document_id}.json", self.boundary_c)
        if approved.exists():
            approved.unlink()
            found = True

        # 4. Delete Token vault entries
        tokens = self._ensure_within_vault(self.token_vault / tenant_id / f"{document_id}.json", self.token_vault)
        if tokens.exists():
            tokens.unlink()

        # 5. Delete metadata
        meta = self._ensure_within_vault(self.meta_vault / tenant_id / f"{document_id}.json", self.meta_vault)
        if meta.exists():
            meta.unlink()
            found = True

        return found


storage_manager = StorageManager()
