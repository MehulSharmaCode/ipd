# backend/app/document_processing/ocr/pan.py
"""
PAN Processor
===============
Wraps the existing Tesseract OCR pipeline for PAN documents and converts
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


class PANProcessor:
    """
    DocumentProcessor-compatible adapter for PAN OCR.

    Usage:
        processor = PANProcessor()
        result = processor.process(file_path, "pan")
    """

    def process(self, file_path: str, doc_type: str) -> ExtractionResult:
        start = time.monotonic()

        # Delegate to existing Tesseract pipeline
        ocr_result = run_ocr_pipeline(file_path, expected_doc_type="pan")
        elapsed_ms = (time.monotonic() - start) * 1000

        # ── Document type mismatch guard ──────────────────────────
        detected_type = (ocr_result.documentType or "").upper()
        if detected_type and "PAN" not in detected_type and detected_type != "UNKNOWN":
            friendly = "Aadhaar card" if "AADHAAR" in detected_type else detected_type
            return ExtractionResult(
                document_type="pan",
                success=False,
                processing_time_ms=elapsed_ms,
                error=f"This appears to be an {friendly}. Please upload a PAN card.",
                validation={"valid": False, "warnings": [f"Document type mismatch: expected PAN, detected {detected_type}"]},
            )

        # Build standardised result
        result = ExtractionResult(
            document_type="pan",
            success=ocr_result.error is None,
            processing_time_ms=elapsed_ms,
            error=ocr_result.error,
            raw_snippet=ocr_result.rawTextSnippet,
        )

        # Confidence: OCR pipeline returns 0–100, we normalise to 0.0–1.0
        overall_confidence = ocr_result.confidence / 100.0 if ocr_result.confidence else 0.0

        # Map extracted fields into the standard schema
        fields = ocr_result.fields or {}
        if fields.get("panNumber"):
            result.set_field("pan_number", fields["panNumber"], overall_confidence)
        if fields.get("name"):
            result.set_field("full_name", fields["name"], overall_confidence)
        if fields.get("fatherName"):
            result.set_field("father_name", fields["fatherName"], overall_confidence)
        if fields.get("dob"):
            result.set_field("dob", fields["dob"], overall_confidence)

        # Carry over validation from the OCR pipeline
        result.validation = ocr_result.validation if isinstance(ocr_result.validation, dict) else {
            "valid": getattr(ocr_result.validation, "valid", False),
            "warnings": getattr(ocr_result.validation, "warnings", []),
        }

        logger.info(
            "PANProcessor: extracted %d fields in %.0fms (valid=%s)",
            len(result.fields), elapsed_ms, result.validation.get("valid"),
        )
        return result
