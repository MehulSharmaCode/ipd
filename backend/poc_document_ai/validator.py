"""
Response Validator
===================
Validates the JSON response from Gemini against the expected schema.

Checks performed:
  - JSON is syntactically valid
  - All required fields are present
  - Data types are correct
  - Values are plausible (not empty strings masquerading as data)
  - No unexpected extra keys
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Expected schema for the extraction response
# ──────────────────────────────────────────────────────────────────────────

EXPECTED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "document_type": (str,),
    "owner_name": (str, type(None)),
    "survey_number": (str, type(None)),
    "gat_number": (str, type(None)),
    "village": (str, type(None)),
    "taluka": (str, type(None)),
    "district": (str, type(None)),
    "land_area": (str, type(None)),
    "current_crop": (str, type(None)),
    "irrigation": (str, type(None)),
    "soil_type": (str, type(None)),
    "ownership_type": (str, type(None)),
    "additional_info": (dict, type(None)),
}

ADDITIONAL_INFO_FIELDS: dict[str, type | tuple[type, ...]] = {
    "co_owners": (list, type(None)),
    "mutation_entries": (str, int, type(None)),
    "hissa_number": (str, type(None)),
    "pot_hissa": (str, type(None)),
    "land_use": (str, type(None)),
    "season": (str, type(None)),
}


class ValidationReport:
    """Structured validation result."""

    def __init__(self):
        self.is_valid_json: bool = False
        self.missing_fields: list[str] = []
        self.type_errors: list[str] = []
        self.empty_fields: list[str] = []
        self.null_fields: list[str] = []
        self.unexpected_keys: list[str] = []
        self.warnings: list[str] = []
        self.populated_fields: list[str] = []

    @property
    def passed(self) -> bool:
        """Overall pass: valid JSON, no missing required fields, no type errors."""
        return (
            self.is_valid_json
            and len(self.missing_fields) == 0
            and len(self.type_errors) == 0
        )

    @property
    def extraction_rate(self) -> float:
        """Percentage of non-null, non-empty fields out of total expected fields."""
        total = len(EXPECTED_FIELDS)
        return len(self.populated_fields) / total if total else 0.0

    def summary(self) -> str:
        lines = []
        lines.append(f"  Valid JSON:       {'✓' if self.is_valid_json else '✗'}")
        lines.append(f"  Overall:          {'PASS' if self.passed else 'FAIL'}")
        lines.append(f"  Extraction Rate:  {self.extraction_rate:.0%} ({len(self.populated_fields)}/{len(EXPECTED_FIELDS)} fields)")

        if self.populated_fields:
            lines.append(f"  Populated:        {', '.join(self.populated_fields)}")
        if self.null_fields:
            lines.append(f"  Null fields:      {', '.join(self.null_fields)}")
        if self.empty_fields:
            lines.append(f"  Empty strings:    {', '.join(self.empty_fields)}")
        if self.missing_fields:
            lines.append(f"  Missing fields:   {', '.join(self.missing_fields)}")
        if self.type_errors:
            lines.append(f"  Type errors:      {'; '.join(self.type_errors)}")
        if self.unexpected_keys:
            lines.append(f"  Unexpected keys:  {', '.join(self.unexpected_keys)}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")

        return "\n".join(lines)


def validate_extraction(data: Optional[dict]) -> ValidationReport:
    """
    Validate a parsed JSON extraction result against the expected schema.

    Parameters:
        data: Parsed JSON dict from Gemini, or None if parsing failed.

    Returns:
        ValidationReport with detailed results.
    """
    report = ValidationReport()

    if data is None:
        report.is_valid_json = False
        report.missing_fields = list(EXPECTED_FIELDS.keys())
        return report

    report.is_valid_json = True

    # ── Check top-level fields ────────────────────────────────────────────
    for field, allowed_types in EXPECTED_FIELDS.items():
        if field not in data:
            report.missing_fields.append(field)
            continue

        value = data[field]

        # Type check
        if not isinstance(value, allowed_types):
            report.type_errors.append(
                f"{field}: expected {_type_names(allowed_types)}, got {type(value).__name__}"
            )
            continue

        # Null check
        if value is None:
            report.null_fields.append(field)
            continue

        # Empty string check
        if isinstance(value, str) and value.strip() == "":
            report.empty_fields.append(field)
            continue

        # Value is populated
        report.populated_fields.append(field)

    # ── Check additional_info sub-fields ──────────────────────────────────
    additional = data.get("additional_info")
    if isinstance(additional, dict):
        for field, allowed_types in ADDITIONAL_INFO_FIELDS.items():
            if field not in additional:
                report.warnings.append(f"additional_info.{field} missing")
                continue

            value = additional[field]
            if not isinstance(value, allowed_types):
                report.type_errors.append(
                    f"additional_info.{field}: expected {_type_names(allowed_types)}, "
                    f"got {type(value).__name__}"
                )

    # ── Check for unexpected keys ─────────────────────────────────────────
    expected_keys = set(EXPECTED_FIELDS.keys())
    actual_keys = set(data.keys())
    unexpected = actual_keys - expected_keys
    if unexpected:
        report.unexpected_keys = sorted(unexpected)

    return report


def validate_analysis(data: Optional[dict]) -> ValidationReport:
    """
    Lightweight validation for the document analysis response (Phase 4).
    """
    report = ValidationReport()

    if data is None:
        report.is_valid_json = False
        return report

    report.is_valid_json = True

    expected = {"document_type", "languages_detected", "content_breakdown",
                "image_quality", "extraction_feasibility"}
    for field in expected:
        if field in data:
            report.populated_fields.append(field)
        else:
            report.missing_fields.append(field)

    return report


def _type_names(types: tuple) -> str:
    """Human-readable type names for error messages."""
    names = []
    for t in types:
        if t is type(None):
            names.append("null")
        else:
            names.append(t.__name__)
    return " | ".join(names)
