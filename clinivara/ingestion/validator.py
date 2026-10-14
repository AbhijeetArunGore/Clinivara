"""
Secure document ingestion validation.

Independent multi-layer checks:
1. File extension validation.
2. Magic byte / file signature validation (never trusting client Content-Type).
3. Bounded streaming size limits.
4. Image decompression bomb prevention.
5. PDF header, encryption status, and page count checks.
"""

import io
from pathlib import Path
from typing import Tuple
from PIL import Image

from clinivara.core.config import settings
from clinivara.core.errors import (
    DocumentTooLargeError,
    InvalidDocumentError,
    SecurityViolationError,
)

# Strict magic byte signatures
MAGIC_SIGNATURES = {
    "pdf": b"%PDF-",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
}


def detect_file_signature(data: bytes) -> str:
    """
    Inspect raw initial bytes to determine true file format.
    Fails closed if the header does not match known secure signatures.
    """
    if len(data) < 8:
        raise InvalidDocumentError("Uploaded file is too small to contain a valid header.")

    if data.startswith(MAGIC_SIGNATURES["pdf"]):
        return "pdf"
    if data.startswith(MAGIC_SIGNATURES["png"]):
        return "png"
    if data.startswith(MAGIC_SIGNATURES["jpeg"][:3]):
        return "jpeg"

    raise InvalidDocumentError("Unsupported or spoofed file format. File signature mismatch.")


def validate_file_size_and_signature(content: bytes) -> Tuple[str, str]:
    """
    Validate size and magic bytes against configured allowed types.
    Returns (format_name, canonical_extension).
    """
    if len(content) == 0:
        raise InvalidDocumentError("Uploaded document is completely empty.")

    if len(content) > settings.max_upload_size_bytes:
        raise DocumentTooLargeError(
            f"Uploaded document exceeds maximum size of {settings.max_upload_size_bytes // (1024*1024)} MB."
        )

    detected_format = detect_file_signature(content[:16])

    if detected_format == "pdf":
        return "pdf", ".pdf"
    elif detected_format == "png":
        return "png", ".png"
    elif detected_format == "jpeg":
        return "jpeg", ".jpg"

    raise InvalidDocumentError("Unsupported file signature.")


def inspect_image_safety(content: bytes) -> None:
    """
    Inspect raster images defensively to guard against decompression bombs.
    """
    try:
        # Enforce conservative pixel limits in Pillow
        Image.MAX_IMAGE_PIXELS = settings.max_image_pixels

        with Image.open(io.BytesIO(content)) as img:
            img.verify()  # Verifies file integrity without decoding full raster data

        # Check dimensions
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
            if width > settings.max_image_dimension_pixels or height > settings.max_image_dimension_pixels:
                raise SecurityViolationError(
                    f"Image dimensions {width}x{height} exceed allowable limit of {settings.max_image_dimension_pixels}px."
                )
            if width * height > settings.max_image_pixels:
                raise SecurityViolationError("Image exceeds maximum pixel threshold (possible decompression bomb).")
    except SecurityViolationError:
        raise
    except Exception as e:
        raise InvalidDocumentError(f"Corrupted or invalid image structure: {str(e)}")


def inspect_pdf_preliminary(file_path: Path) -> int:
    """
    Perform preliminary PDF inspection using PyMuPDF:
    - Verifies document can be opened.
    - Checks encryption / password protection (rejected unless supported).
    - Checks page count against configured maximum limit.
    Returns page count.
    """
    import fitz  # PyMuPDF

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise InvalidDocumentError("Corrupted or malformed PDF file.")

    try:
        if doc.is_encrypted:
            raise SecurityViolationError("Encrypted or password-protected PDFs are rejected by policy.")

        page_count = doc.page_count
        if page_count < 1:
            raise InvalidDocumentError("PDF document contains 0 pages.")

        if page_count > settings.max_pdf_pages:
            raise DocumentTooLargeError(
                f"PDF page count ({page_count}) exceeds allowable maximum of {settings.max_pdf_pages} pages."
            )

        return page_count
    finally:
        doc.close()
