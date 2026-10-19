"""
Regular expression patterns and context keywords for clinical and regional identifiers.
Includes Indian healthcare identifiers (Aadhaar, PAN, ABHA/UHID) and hospital MRN patterns.
"""

# Indian Aadhaar pattern: 12 digits, often grouped in 4-4-4
AADHAAR_REGEX = r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"
AADHAAR_CONTEXT = ["aadhaar", "aadhar", "uid", "uidai", "gov id", "national id"]

# Indian Permanent Account Number (PAN): 5 uppercase letters, 4 digits, 1 uppercase letter
PAN_REGEX = r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
PAN_CONTEXT = ["pan", "pan card", "income tax", "tax id"]

# Ayushman Bharat Health Account (ABHA) ID / Address: 14 digits formatted as 12-3456-7890-1234
ABHA_NUMBER_REGEX = r"\b\d{2}-\d{4}-\d{4}-\d{4}\b"
ABHA_CONTEXT = ["abha", "ndhm", "ayushman", "health id", "pmjay"]

# Hospital Medical Record Number (MRN) / Unique Hospital ID (UHID)
# Structured patterns like MRN-12345, UHID: 987654, HSP-4567, PID: A123456
HOSPITAL_MRN_REGEX = r"\b(?:MRN|UHID|PID|HSP|HOSP|IPD|OPD)[-:\s#]{1,3}[A-Z0-9\-/]{4,16}\b"
MRN_CONTEXT = [
    "mrn",
    "uhid",
    "medical record",
    "record number",
    "patient id",
    "chart number",
    "ipd no",
    "opd no",
    "admission no",
    "case no",
    "reg no",
    "registration",
]

# Indian Phone Numbers (+91 or starting with 6, 7, 8, 9)
INDIAN_PHONE_REGEX = r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b"
PHONE_CONTEXT = ["phone", "tel", "mobile", "contact", "cell", "call", "whatsapp"]

# Generic Doctor / Healthcare Provider prefix patterns
DOCTOR_NAME_PREFIX_REGEX = r"\b(?:Dr\.|Dr|Doctor|Prof\.|Prof)[ \t]+([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,3})\b"
DOCTOR_CONTEXT = ["dr", "physician", "consultant", "attending", "specialist", "surgeon", "pathologist"]
