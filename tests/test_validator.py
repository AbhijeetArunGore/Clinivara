"""
Unit tests for ingestion validation, magic bytes, size limits, and security constraints.
"""

import io
import pytest
from PIL import Image
import fitz

from clinivara.core.errors import (
    DocumentTooLargeError,
    InvalidDocumentError,
    SecurityViolationError,
)
from clinivara.ingestion.validator import (
    detect_file_signature,
    inspect_image_safety,
    inspect_pdf_preliminary,
    validate_file_size_and_signature,
)


def test_magic_byte_detection():
    # Valid PDF
    assert detect_file_signature(b"%PDF-1.7\n%fake") == "pdf"
    # Valid PNG
    assert detect_file_signature(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR") == "png"
    # Valid JPEG
    assert detect_file_signature(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01") == "jpeg"

    # Corrupt or spoofed header
    with pytest.raises(InvalidDocumentError):
        detect_file_signature(b"<html><script>alert(1)</script></html>")

    with pytest.raises(InvalidDocumentError):
        detect_file_signature(b"")


def test_empty_document_rejection():
    with pytest.raises(InvalidDocumentError):
        validate_file_size_and_signature(b"")


def test_spoofed_mime_type_rejection():
    # Fake file claiming to be pdf
    fake_pdf = b"This is just plain text, not a PDF header."
    with pytest.raises(InvalidDocumentError):
        validate_file_size_and_signature(fake_pdf)


def test_image_decompression_bomb_rejection():
    # Construct an oversized dimension image
    img = Image.new("RGB", (9000, 100), color=(255, 255, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    oversized_bytes = buffer.getvalue()

    with pytest.raises(SecurityViolationError) as exc_info:
        inspect_image_safety(oversized_bytes)
    assert "exceed allowable limit" in str(exc_info.value)


def test_encrypted_pdf_rejection(tmp_path):
    # Create encrypted PDF
    pdf_path = tmp_path / "encrypted.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Confidential Medical Data")
    doc.save(
        str(pdf_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="securepass",
        owner_pw="ownerpass",
    )
    doc.close()

    with pytest.raises(SecurityViolationError) as exc_info:
        inspect_pdf_preliminary(pdf_path)
    assert "Encrypted or password-protected" in str(exc_info.value)
