"""
OCR Pipeline Orchestrator
--------------------------
Responsibility: Chain all OCR modules into a single cohesive workflow.

This is the ONLY entry point that the upload API should call.
No other module orchestrates the full pipeline.

Pipeline stages (in order):
  1. Validation      — check file exists, type is supported
  2. OCR Service     — extract raw text via Tesseract
  3. Classification  — identify document type
  4. Parser          — extract structured fields
  5. Validation      — validate extracted field values
  6. Mapping         — map fields to farmer profile schema
  7. Response        — return structured OCRPipelineResult

Design: Each stage is independently testable. This module only wires them together.
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.ml.ocr.ocr_service import extract_text, OCRResult
from app.ml.ocr.classification import classify, ClassificationResult
from app.ml.ocr.parsers import get_parser
from app.ml.ocr.validation import validate_fields, ValidationResult
from app.ml.ocr.mapping import map_to_profile

logger = logging.getLogger(__name__)

# Supported file types for upload validation
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


@dataclass
class OCRPipelineResult:
    """
    The structured response returned by the OCR pipeline.
    This becomes the JSON body sent to the frontend.

    Matches the agreed API contract:
    {
      "documentType": "AADHAAR_FRONT",
      "confidence": 94,
      "fields": { "name": "...", "aadhaarNumber": "...", ... },
      "validation": { "valid": true, "warnings": [] },
      "profileSuggestions": { "full_name_ocr_suggestion": "...", "gender": "Male", ... },
      "rawTextSnippet": "..."   # first 300 chars, for debugging only
    }
    """
    documentType: str
    confidence: float               # 0–100
    fields: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    profileSuggestions: dict = field(default_factory=dict)
    rawTextSnippet: str = ""
    processingTimeMs: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "documentType": self.documentType,
            "confidence": round(self.confidence, 1),
            "fields": self.fields,
            "validation": self.validation,
            "profileSuggestions": self.profileSuggestions,
            "rawTextSnippet": self.rawTextSnippet,
            "processingTimeMs": round(self.processingTimeMs, 1),
        }
        if self.error:
            d["error"] = self.error
        return d


def _make_error_result(error_msg: str, processing_ms: float = 0.0) -> OCRPipelineResult:
    return OCRPipelineResult(
        documentType="UNKNOWN",
        confidence=0.0,
        validation={"valid": False, "warnings": [error_msg]},
        error=error_msg,
        processingTimeMs=processing_ms,
    )


def process(file_path: str, expected_doc_type: Optional[str] = None) -> OCRPipelineResult:
    """
    Run the full OCR pipeline on an uploaded document.

    Args:
        file_path: Absolute path to the saved file.
        expected_doc_type: Optional hint from the user (e.g., "aadhar", "pan").
                           Used only for early mismatch detection, not enforced.
    Returns:
        OCRPipelineResult with all extracted and validated data.
    """
    pipeline_start = time.monotonic()

    # ── Stage 1: File Validation ─────────────────────────────────────
    if not os.path.isfile(file_path):
        return _make_error_result(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return _make_error_result(
            f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    logger.info(f"Pipeline START: '{os.path.basename(file_path)}' (hint='{expected_doc_type}')")

    # ── Stage 2: OCR Text Extraction ─────────────────────────────────
    try:
        ocr_result: OCRResult = extract_text(file_path)
    except RuntimeError as e:
        # Tesseract not found or unavailable
        logger.error(f"OCR Service failure: {e}")
        return _make_error_result(f"OCR engine unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected OCR error: {e}", exc_info=True)
        return _make_error_result(f"OCR processing failed: {str(e)}")

    if not ocr_result.text.strip():
        return _make_error_result(
            "OCR produced no text. The image may be blank or too low quality.",
            processing_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    raw_snippet = ocr_result.text[:300]

    # ── Stage 3: Document Classification ─────────────────────────────
    classification: ClassificationResult = classify(ocr_result.text)
    doc_type_used = classification.document_type

    # Early mismatch warning or fallback if UNKNOWN
    if expected_doc_type:
        hint_upper = expected_doc_type.upper().strip()
        actual_upper = classification.document_type.upper()

        hint_is_aadhaar = any(k in hint_upper for k in ["AADH", "AADHAAR", "ADHAR"])
        hint_is_pan = "PAN" in hint_upper
        hint_is_satbara = any(k in hint_upper for k in ["SATBARA", "7/12", "7_12", "LAND"])

        actual_is_aadhaar = "AADHAAR" in actual_upper
        actual_is_pan = "PAN" in actual_upper
        actual_is_satbara = "SATBARA" in actual_upper

        # Fallback handling: if classification was UNKNOWN, rely on user's hint
        if classification.document_type == "UNKNOWN":
            if hint_is_aadhaar:
                doc_type_used = "AADHAAR_FRONT"
                logger.info(f"Classification UNKNOWN — using hint fallback: '{doc_type_used}'")
            elif hint_is_pan:
                doc_type_used = "PAN"
                logger.info(f"Classification UNKNOWN — using hint fallback: '{doc_type_used}'")
            elif hint_is_satbara:
                doc_type_used = "SATBARA_7_12"
                logger.info(f"Classification UNKNOWN — using hint fallback: '{doc_type_used}'")
        elif (hint_is_aadhaar and not actual_is_aadhaar) or (hint_is_pan and not actual_is_pan) or (hint_is_satbara and not actual_is_satbara):
            logger.warning(
                f"Document type mismatch: user specified hint '{expected_doc_type}', "
                f"classified as '{classification.document_type}'"
            )

    if doc_type_used == "UNKNOWN":
        total_ms = (time.monotonic() - pipeline_start) * 1000
        return OCRPipelineResult(
            documentType="UNKNOWN",
            confidence=0.0,
            validation={
                "valid": False,
                "warnings": ["Could not identify the document type. "
                             "Please ensure the document is a legible Aadhaar card, PAN card, or 7/12 Satbara."]
            },
            rawTextSnippet=raw_snippet,
            processingTimeMs=total_ms,
        )

    # ── Stage 4: Field Extraction ─────────────────────────────────────
    parser = get_parser(doc_type_used)
    extracted_fields = {}
    if parser:
        try:
            extracted_fields = parser.extract(ocr_result.text)
        except Exception as e:
            logger.error(f"Parser error for '{doc_type_used}': {e}", exc_info=True)
            extracted_fields = {}
    else:
        logger.warning(f"No parser for type '{doc_type_used}'")

    # ── Stage 5: Validation ───────────────────────────────────────────
    validation_result: ValidationResult = validate_fields(
        doc_type_used, extracted_fields
    )

    # ── Stage 6: Profile Mapping ──────────────────────────────────────
    profile_suggestions = {}
    try:
        profile_suggestions = map_to_profile(doc_type_used, extracted_fields)
    except Exception as e:
        logger.error(f"Profile mapping error: {e}", exc_info=True)

    # ── Stage 7: Build Response ───────────────────────────────────────
    total_ms = (time.monotonic() - pipeline_start) * 1000
    class_conf = classification.confidence if classification.document_type != "UNKNOWN" else 0.7
    blended_confidence = (ocr_result.confidence * 0.6) + (class_conf * 100 * 0.4)

    logger.info(
        f"Pipeline DONE: type={doc_type_used}, "
        f"fields={list(extracted_fields.keys())}, "
        f"valid={validation_result.valid}, "
        f"total_ms={total_ms:.0f}"
    )

    return OCRPipelineResult(
        documentType=doc_type_used,
        confidence=blended_confidence,
        fields=extracted_fields,
        validation={
            "valid": validation_result.valid,
            "warnings": validation_result.warnings,
        },
        profileSuggestions=profile_suggestions,
        rawTextSnippet=raw_snippet,
        processingTimeMs=total_ms,
    )
