# backend/app/document_processing/ocr/aadhaar.py
"""
Aadhaar Processor
===================
Wraps the existing Tesseract OCR pipeline for Aadhaar documents and converts
its output into the standardised ExtractionResult schema.

This adapter does NOT rewrite any OCR logic — it delegates to:
    app.ml.ocr.pipeline.process()

and translates the OCRPipelineResult into ExtractionResult.
"""

import time
import logging

from app.ml.ocr.pipeline import process as run_ocr_pipeline
from app.document_processing.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class AadhaarProcessor:
    """
    DocumentProcessor-compatible adapter for Aadhaar OCR.

    Usage:
        processor = AadhaarProcessor()
        result = processor.process(file_path, "aadhar")
    """

    def process(self, file_path: str, doc_type: str) -> ExtractionResult:
        start = time.monotonic()

        # Delegate to existing Tesseract pipeline
        ocr_result = run_ocr_pipeline(file_path, expected_doc_type="aadhar")
        elapsed_ms = (time.monotonic() - start) * 1000

        # ── Document type mismatch guard ──────────────────────────
        detected_type = (ocr_result.documentType or "").upper()
        if detected_type and "AADHAAR" not in detected_type and detected_type != "UNKNOWN":
            friendly = "PAN card" if "PAN" in detected_type else detected_type
            return ExtractionResult(
                document_type="aadhar",
                success=False,
                processing_time_ms=elapsed_ms,
                error=f"This appears to be a {friendly}. Please upload an Aadhaar card.",
                validation={"valid": False, "warnings": [f"Document type mismatch: expected Aadhaar, detected {detected_type}"]},
            )

        # Build standardised result
        result = ExtractionResult(
            document_type="aadhar",
            success=ocr_result.error is None,
            processing_time_ms=elapsed_ms,
            error=ocr_result.error,
            raw_snippet=ocr_result.rawTextSnippet,
        )

        # Confidence: OCR pipeline returns 0–100, we normalise to 0.0–1.0
        overall_confidence = ocr_result.confidence / 100.0 if ocr_result.confidence else 0.0

        # Map extracted fields into the standard schema
        fields = ocr_result.fields or {}
        if fields.get("aadhaarNumber"):
            result.set_field("aadhar_number", fields["aadhaarNumber"], overall_confidence)
        if fields.get("name"):
            result.set_field("full_name", fields["name"], overall_confidence)
        if fields.get("dob"):
            result.set_field("dob", fields["dob"], overall_confidence)
        if fields.get("birthYear"):
            result.set_field("birth_year", fields["birthYear"], overall_confidence)
        if fields.get("gender"):
            result.set_field("gender", fields["gender"], overall_confidence)

        # Carry over validation from the OCR pipeline
        result.validation = ocr_result.validation if isinstance(ocr_result.validation, dict) else {
            "valid": getattr(ocr_result.validation, "valid", False),
            "warnings": getattr(ocr_result.validation, "warnings", []),
        }

        logger.info(
            "AadhaarProcessor: extracted %d fields in %.0fms (valid=%s)",
            len(result.fields), elapsed_ms, result.validation.get("valid"),
        )
        return result
