"""
Security primitives: hashing, constant-time authentication, sanitization,
and cryptographically secure token generation.
"""

import hashlib
import hmac
import os
import re
import secrets
import uuid
from pathlib import Path
from typing import Optional

from clinivara.core.config import settings
from clinivara.core.errors import SecurityViolationError, UnauthorizedAccessError


def generate_document_id() -> str:
    """Generate a cryptographically secure random document ID."""
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """Generate a correlation ID for request tracking and audit linkage."""
    return f"corr_{secrets.token_hex(8)}"


def calculate_sha256_digest(file_path: Path, chunk_size: int = 65536) -> str:
    """
    Calculate the SHA-256 digest of a staged file using bounded chunk streaming.
    Does not load arbitrarily large files into memory.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize user-provided filename:
    - Strips directory components to prevent path traversal
    - Removes null bytes and dangerous shell characters
    - Returns a safe base name (never used directly as a filesystem storage name).
    """
    if not filename:
        return "unnamed_document"

    # Reject null bytes
    if "\x00" in filename:
        raise SecurityViolationError("Filename contains illegal null bytes.")

    # Strip directory paths
    base_name = os.path.basename(filename.replace("\\", "/"))

    # Remove any characters outside alphanumeric, dash, underscore, dot
    sanitized = re.sub(r"[^a-zA-Z0-9_\.-]", "_", base_name)
    sanitized = sanitized.strip("._")

    if not sanitized:
        sanitized = "unnamed_document"

    return sanitized[:128]


def verify_api_key(provided_key: Optional[str]) -> str:
    """
    Verify client API key using constant-time comparison to prevent timing attacks.
    Returns the associated tenant/client ID if valid.
    """
    if not provided_key:
        raise UnauthorizedAccessError("Missing API key authentication header.")

    for valid_key, tenant_id in settings.api_keys.items():
        if secrets.compare_digest(provided_key.encode("utf-8"), valid_key.encode("utf-8")):
            return tenant_id

    raise UnauthorizedAccessError("Invalid or revoked API key.")


def generate_pseudonym_token(entity_type: str, raw_value: str, salt: Optional[str] = None) -> str:
    """
    Generate a cryptographically secure pseudonymous token using HMAC-SHA256.
    Protects against dictionary attacks by using a high-entropy secret salt.
    Does NOT leak the original identifier or use unsalted hashes.
    """
    active_salt = (salt or settings.tokenization_salt).encode("utf-8")
    mac = hmac.new(active_salt, f"{entity_type}:{raw_value.strip().lower()}".encode("utf-8"), hashlib.sha256)
    short_token = mac.hexdigest()[:12].upper()
    return f"[{entity_type}_{short_token}]"
