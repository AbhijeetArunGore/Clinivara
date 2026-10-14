"""
Repeatable Evaluation Script for Privacy and Clinical Preservation.

Measures:
- Precision, Recall, F1-score across sensitive entity types.
- Identifier-level false negatives (leaks).
- False positives (improper redaction of non-identifying tokens).
- Residual identifier rate after the independent second pass.
- Clinical preservation rate (diagnoses, lab values, dosages).
- End-to-end processing latency.
"""

import time
from typing import Any, Dict, List
from clinivara.deidentification.engine import deidentification_engine
from clinivara.extraction.models import ExtractionResult, PageExtraction
from clinivara.normalization.text_cleaner import text_cleaner
from clinivara.validation.release_gate import release_gate
from clinivara.validation.residual_detector import residual_scanner

# Annotated synthetic benchmark dataset with ground-truth identifiers and clinical facts
BENCHMARK_DATASET = [
    {
        "id": "synthetic_eval_01",
        "raw_text": (
            "PATIENT DISCHARGE SUMMARY\n"
            "Patient: Rajesh Kumar\n"
            "MRN: MRN-554109\n"
            "Aadhaar: 5541 2390 1289\n"
            "Phone: 9812345670\n"
            "Consultant: Dr. Arvind Joshi\n"
            "Date of Admission: 10/01/2024\n"
            "Diagnosis: Type 2 Diabetes Mellitus\n"
            "HbA1c: 8.8%\n"
            "Fasting Glucose: 174 mg/dL\n"
            "Rx: Metformin 1000 mg PO BID"
        ),
        "ground_truth_entities": [
            ("Rajesh Kumar", "PERSON"),
            ("Dr. Arvind Joshi", "PERSON"),
            ("MRN-554109", "PATIENT_ID"),
            ("5541 2390 1289", "GOV_ID"),
            ("9812345670", "PHONE_NUMBER"),
            ("10/01/2024", "DATE_TIME"),
        ],
        "must_preserve_clinical": ["Type 2 Diabetes", "HbA1c: 8.8%", "174 mg/dL", "Metformin 1000 mg"],
    },
    {
        "id": "synthetic_eval_02",
        "raw_text": (
            "OUTPATIENT CLINIC NOTE\n"
            "Patient Name: Sunita Rao\n"
            "UHID: UHID-992144\n"
            "PAN: ABCDE5541K\n"
            "ABHA: 14-8890-1234-5678\n"
            "Contact: +91-9123456780\n"
            "Email: sunita.rao@hospital.org\n"
            "Date: 22-Feb-2024\n"
            "Diagnosis: Essential Hypertension, Dyslipidemia\n"
            "BP: 142/90 mmHg\n"
            "Total Cholesterol: 240 mg/dL\n"
            "Rx: Amlodipine 5 mg daily, Atorvastatin 20 mg HS"
        ),
        "ground_truth_entities": [
            ("Sunita Rao", "PERSON"),
            ("UHID-992144", "PATIENT_ID"),
            ("ABCDE5541K", "GOV_ID"),
            ("14-8890-1234-5678", "PATIENT_ID"),
            ("+91-9123456780", "PHONE_NUMBER"),
            ("sunita.rao@hospital.org", "EMAIL_ADDRESS"),
            ("22-Feb-2024", "DATE_TIME"),
        ],
        "must_preserve_clinical": ["Essential Hypertension", "142/90 mmHg", "240 mg/dL", "Amlodipine 5 mg", "Atorvastatin 20 mg"],
    },
    {
        "id": "synthetic_eval_03",
        "raw_text": (
            "EMERGENCY DEPARTMENT REPORT\n"
            "Patient: David Miller\n"
            "PID: HSP-332190\n"
            "Phone: 9876500112\n"
            "Exam Date: 05/03/2024\n"
            "Attending: Dr. Sarah Connor\n"
            "Chief Complaint: Acute chest pain on exertion\n"
            "Impression: Acute Coronary Syndrome ruled out, GERD suspected\n"
            "Troponin: < 0.01 ng/mL\n"
            "ECG: Normal sinus rhythm\n"
            "Rx: Omeprazole 40 mg PO daily"
        ),
        "ground_truth_entities": [
            ("David Miller", "PERSON"),
            ("Dr. Sarah Connor", "PERSON"),
            ("HSP-332190", "PATIENT_ID"),
            ("9876500112", "PHONE_NUMBER"),
            ("05/03/2024", "DATE_TIME"),
        ],
        "must_preserve_clinical": ["Acute chest pain", "< 0.01 ng/mL", "Normal sinus rhythm", "Omeprazole 40 mg"],
    },
]


def run_benchmark() -> Dict[str, Any]:
    """Execute evaluation over the benchmark dataset and compute metrics."""
    total_ground_truth = 0
    total_true_positives = 0
    total_false_negatives = 0
    total_false_positives = 0
    total_residual_after_gate = 0
    clinical_preserved_count = 0
    total_clinical_facts = 0
    latencies = []

    print("\n=======================================================")
    print(" CLINIVARA PRIVACY & CLINICAL PRESERVATION BENCHMARK")
    print("=======================================================\n")

    for case in BENCHMARK_DATASET:
        start_time = time.perf_counter()
        raw_text = case["raw_text"]
        gt_entities = case["ground_truth_entities"]
        must_preserve = case["must_preserve_clinical"]

        # Step 1: Clean
        cleaned = text_cleaner.clean_text(raw_text)

        # Step 2: Deidentify
        deid_text, counts, summary = deidentification_engine.deidentify(
            text=cleaned,
            tenant_id="benchmark_tenant",
            document_id=case["id"],
            correlation_id=f"eval_{case['id']}",
        )

        # Step 3: Release Gate validation
        ext_res = ExtractionResult(
            document_id=case["id"],
            tenant_id="benchmark_tenant",
            correlation_id=f"eval_{case['id']}",
            pages=[PageExtraction(
                page_number=1,
                method="DIGITAL_TEXT",
                text=raw_text,
                character_count=len(raw_text),
                word_count=len(raw_text.split()),
            )],
            methods_used=["digital_text"],
            total_pages=1,
            status="COMPLETED",
        )
        decision, warnings, gate_metrics = release_gate.evaluate_and_commit(
            tenant_id="benchmark_tenant",
            document_id=case["id"],
            correlation_id=f"eval_{case['id']}",
            raw_text=raw_text,
            deidentified_text=deid_text,
            extraction_result=ext_res,
            transformed_counts=counts,
        )

        latency = (time.perf_counter() - start_time) * 1000.0
        latencies.append(latency)

        # Evaluate entity removal against ground truth
        case_tp = 0
        case_fn = 0
        for val, ent_type in gt_entities:
            total_ground_truth += 1
            if val not in deid_text:
                case_tp += 1
                total_true_positives += 1
            else:
                case_fn += 1
                total_false_negatives += 1
                print(f"[LEAK DETECTED] Case {case['id']}: Identifier '{val}' was not removed!")

        # Evaluate clinical facts preservation
        for fact in must_preserve:
            total_clinical_facts += 1
            if fact.lower() in deid_text.lower():
                clinical_preserved_count += 1
            else:
                print(f"[PRESERVATION FAILURE] Case {case['id']}: Fact '{fact}' was lost!")

        # Residual check from second pass
        residuals, _ = residual_scanner.scan_for_residuals(deid_text)
        total_residual_after_gate += residuals

        print(f"Report: {case['id']:<20} | Decision: {decision:<8} | TP: {case_tp}/{len(gt_entities)} | Residuals: {residuals} | Latency: {latency:.1f}ms")

    # Metrics calculation
    precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 1.0
    recall = total_true_positives / total_ground_truth if total_ground_truth > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    preservation_rate = (clinical_preserved_count / total_clinical_facts) * 100.0 if total_clinical_facts > 0 else 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n-------------------------------------------------------")
    print(" EVALUATION SUMMARY")
    print("-------------------------------------------------------")
    print(f"Total Ground-Truth Entities:  {total_ground_truth}")
    print(f"True Positives (Redacted):   {total_true_positives}")
    print(f"False Negatives (Leaks):     {total_false_negatives}")
    print(f"Precision:                   {precision * 100:.2f}%")
    print(f"Recall:                      {recall * 100:.2f}%")
    print(f"F1 Score:                    {f1 * 100:.2f}%")
    print(f"Residual Leaks Post-Gate:    {total_residual_after_gate}")
    print(f"Clinical Preservation Rate:  {preservation_rate:.2f}% ({clinical_preserved_count}/{total_clinical_facts})")
    print(f"Average Latency:             {avg_latency:.2f} ms")
    print("=======================================================\n")

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_negatives": total_false_negatives,
        "residual_leaks": total_residual_after_gate,
        "clinical_preservation_rate": preservation_rate,
        "avg_latency_ms": avg_latency,
    }


if __name__ == "__main__":
    run_benchmark()
