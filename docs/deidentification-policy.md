# Clinivara De-identification Policy & Taxonomy

## 1. Supported Entity Taxonomy

Clinivara detects and sanitizes direct identifiers, document-level identifiers, and indirect quasi-identifiers:

### Direct Identifiers
- **Patient & Relative Names** (`PERSON`): Full names, surnames, nicknames, relative names.
- **Healthcare Professionals** (`PERSON` / `DOCTOR`): Attending physicians, consultants, surgeons, referring clinicians (detected via contextual prefixes `Dr.`, `Doctor`, `Prof.`).
- **Hospital Medical Record Numbers** (`PATIENT_ID` / `MRN`): Structured hospital IDs, UHID, PID, IPD/OPD numbers (`HSP-XXXX`, `MRN-XXXX`, `UHID: XXXX`).
- **Indian National Identifiers** (`GOV_ID`):
  - **Aadhaar**: 12-digit grouped sequences (`\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b`).
  - **PAN Card**: 10-character alphanumeric sequences (`[A-Z]{5}[0-9]{4}[A-Z]`).
  - **ABHA Number**: 14-digit Ayushman Bharat Health Account IDs (`\b\d{2}-\d{4}-\d{4}-\d{4}\b`).
- **Phone Numbers** (`PHONE_NUMBER`): Indian mobile numbers (`+91 ...`, 10-digit formats starting with 6-9) and international formats.
- **Email Addresses** (`EMAIL_ADDRESS`): Standard email formats.
- **Dates** (`DATE_TIME`): Exact dates of birth, admission, discharge, exam dates.

---

## 2. Transformation Policies

The policy supports entity-specific handling:

| Entity Category | Default Action | Mask Pattern / Output |
| :--- | :--- | :--- |
| `PERSON` (Patient / Relative) | Irreversible Redaction | `[NAME]` |
| `PERSON` (Doctor / Clinician) | Irreversible Redaction | `[NAME]` |
| `PATIENT_ID` / `MRN` / `UHID` | Redaction (or Tokenization) | `[PATIENT_ID]` (or `[PATIENT_ID_4B7F1C9]`) |
| `GOV_ID` (Aadhaar / PAN) | Irreversible Redaction | `[GOV_ID]` |
| `PHONE_NUMBER` | Irreversible Redaction | `[PHONE]` |
| `EMAIL_ADDRESS` | Irreversible Redaction | `[EMAIL]` |
| `DATE_TIME` | Configurable | `[DATE]` (or `[DATE_YEAR_2024]` if `generalize_year`) |
| `LOCATION` | Irreversible Redaction | `[LOCATION]` |

---

## 3. Clinical Whitelist & Medical Utility Preservation

De-identification must not degrade clinical utility. Clinivara enforces an active clinical whitelist and context protection:
- **Diagnoses**: Terms such as *Type 2 Diabetes, Hypertension, Asthma, Pneumonia, Anemia* are never redacted.
- **Laboratory Tests**: *HbA1c, Fasting Blood Glucose, Serum Creatinine, Bilirubin, WBC, Platelets* are preserved.
- **Medications & Dosages**: *Metformin 500 mg, Lisinopril 10 mg, Atorvastatin 20 mg PO BID* remain intact.
- **Clinical Operators & Units**: Signs such as `<`, `>`, `≤`, `≥`, `±`, `-`, `%`, `mg/dL`, `mmol/L`, `mmHg` are preserved.

---

## 4. Residual Risk & Regulatory Scope

1. **Not a Formal Certification**: Passing technical de-identification tests does not constitute formal certification under HIPAA or India's DPDP Act.
2. **Re-identification Risk**: High-risk research deployments must incorporate expert statistical risk determination.
3. **Fail-Closed Gate**: If any direct identifier leaks past the primary detector, the second-pass scanner rejects release (`REJECTED` status).
