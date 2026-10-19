"""Pytest configuration, fixtures, and synthetic document generators."""

import io
import os

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

# Test-only keys are deliberately fake and set before application settings are imported.
os.environ.setdefault(
    "CLINIVARA_API_KEYS",
    '{"FAKE_TEST_API_KEY_ALPHA":"clinic_default_tenant","FAKE_TEST_API_KEY_BETA":"clinic_tenant_two"}',
)

from clinivara.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid test-only authentication header for the default tenant."""
    return {"X-API-Key": "FAKE_TEST_API_KEY_ALPHA"}


@pytest.fixture
def tenant_two_headers():
    """Valid test-only authentication header for the second tenant."""
    return {"X-API-Key": "FAKE_TEST_API_KEY_BETA"}


@pytest.fixture
def sample_clinical_text():
    """Realistic synthetic clinical report containing identifiable details and clinical metrics."""
    return (
        "HOSPITAL DISCHARGE SUMMARY\n"
        "Patient Name: Johnathan Doe\n"
        "DOB: 12/04/1982\n"
        "MRN: MRN-8849201\n"
        "Aadhaar Number: 4589 1234 5678\n"
        "Contact: +91-9876543210\n"
        "Attending Physician: Dr. Rajesh Sharma\n"
        "Email: j.doe.patient@healthcare.example.org\n\n"
        "CHIEF COMPLAINT:\n"
        "Patient presents with persistent fatigue and blurred vision.\n\n"
        "PAST MEDICAL HISTORY:\n"
        "Type 2 Diabetes, Hypertension.\n\n"
        "CURRENT MEDICATIONS:\n"
        "Metformin 500 mg PO BID, Lisinopril 10 mg daily.\n\n"
        "LABORATORY RESULTS:\n"
        "HbA1c: 8.4%\n"
        "Fasting Blood Glucose: 162 mg/dL\n"
        "Serum Creatinine: 1.1 mg/dL\n"
        "Blood Pressure: 135/85 mmHg\n\n"
        "ASSESSMENT & PLAN:\n"
        "Uncontrolled Type 2 Diabetes Mellitus.\n"
        "Increase Metformin to 1000 mg PO BID.\n"
        "Follow up in 4 weeks."
    )


@pytest.fixture
def synthetic_pdf_bytes(sample_clinical_text):
    """Generate in-memory synthetic PDF with embedded digital text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_text(fitz.Point(50, 72), sample_clinical_text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def synthetic_image_bytes():
    """Generate in-memory synthetic PNG raster image with text for OCR testing."""
    img = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    text = (
        "CLINICAL LABORATORY REPORT\n"
        "Patient: Alice Johnson\n"
        "PID: HSP-99214\n"
        "Phone: 9876501234\n"
        "Test: HbA1c: 7.1%\n"
        "Diagnosis: Diabetes"
    )
    draw.text((30, 30), text, fill=(0, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
