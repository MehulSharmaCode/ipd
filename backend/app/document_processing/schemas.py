# backend/app/document_processing/schemas.py
"""
Standardised Extraction Schema
================================
Every document processor (OCR-based or Vision-based) MUST return an
ExtractionResult that follows this schema.

This is the contract between the processing engine and the Profile Builder.

Design rationale:
  - Each extracted field carries its own value, source_document, and confidence
    so the Profile Builder can apply precedence rules when merging data from
    multiple documents (e.g. Aadhaar + PAN + 7/12).
  - The top-level ExtractionResult also carries an overall status, the
    document type, and processing metadata.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExtractedField:
    """
    A single field extracted from a document.

    Attributes:
        value:           The extracted value (string, number, list, etc.).
        source_document: Which document type produced this value
                         (e.g. "aadhar", "pan", "7_12").
        confidence:      Extraction confidence between 0.0 and 1.0.
    """
    value: Any
    source_document: str
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "source_document": self.source_document,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ExtractionResult:
    """
    Standardised output from any document processor.

    Attributes:
        document_type:    Canonical type string (e.g. "aadhar", "pan", "7_12").
        success:          Whether the extraction completed without fatal errors.
        fields:           Dict of field_name -> ExtractedField.
        validation:       Dict with 'valid' (bool) and 'warnings' (list[str]).
        processing_time_ms: How long the extraction took in milliseconds.
        error:            Error message if success is False.
        raw_snippet:      First ~300 chars of raw text (debug aid for OCR).
    """
    document_type: str
    success: bool = True
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    validation: dict = field(default_factory=lambda: {"valid": True, "warnings": []})
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    raw_snippet: str = ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def set_field(self, name: str, value: Any, confidence: float = 1.0) -> None:
        """Convenience method to add/update an extracted field."""
        if value is not None:
            self.fields[name] = ExtractedField(
                value=value,
                source_document=self.document_type,
                confidence=confidence,
            )

    def get_value(self, name: str, default: Any = None) -> Any:
        """Get the raw value for a field, or default if missing."""
        f = self.fields.get(name)
        return f.value if f is not None else default

    @property
    def populated_field_names(self) -> list[str]:
        return list(self.fields.keys())

    @property
    def extraction_rate(self) -> float:
        """Fraction of fields that have non-None values."""
        if not self.fields:
            return 0.0
        populated = sum(1 for f in self.fields.values() if f.value is not None)
        return populated / len(self.fields)

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON responses."""
        return {
            "document_type": self.document_type,
            "success": self.success,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "validation": self.validation,
            "processing_time_ms": round(self.processing_time_ms, 1),
            "error": self.error,
        }

    @staticmethod
    def make_error(document_type: str, error_msg: str,
                   processing_time_ms: float = 0.0) -> "ExtractionResult":
        """Factory for a failed extraction result."""
        return ExtractionResult(
            document_type=document_type,
            success=False,
            validation={"valid": False, "warnings": [error_msg]},
            error=error_msg,
            processing_time_ms=processing_time_ms,
        )
