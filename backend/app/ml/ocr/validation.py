"""
Validation Engine
-----------------
Responsibility: Validate extracted field values and return structured warnings.
Does NOT modify values — it only validates and annotates.

Validators follow a consistent pattern:
  validate_xxx(value) -> (is_valid: bool, warning: str | None)
"""

import re
import logging
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Individual field validators
# ──────────────────────────────────────────────────────────────

def validate_aadhaar_number(value: str) -> Tuple[bool, Optional[str]]:
    """
    Aadhaar: must be exactly 12 digits when spaces are removed.
    First digit must not be 0 or 1 (UIDAI specification).
    """
    digits = re.sub(r"\s", "", value)
    if not digits.isdigit():
        return False, "Aadhaar number must contain only digits."
    if len(digits) != 12:
        return False, f"Aadhaar number must be 12 digits (got {len(digits)})."
    if digits[0] in {"0", "1"}:
        return False, "Aadhaar number cannot start with 0 or 1."
    return True, None


def validate_pan_number(value: str) -> Tuple[bool, Optional[str]]:
    """
    PAN: must match the pattern AAAAA9999A (5 uppercase letters, 4 digits, 1 uppercase letter).
    """
    pattern = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    if not pattern.match(value.upper()):
        return False, f"'{value}' does not match the PAN format (e.g., ABCDE1234F)."
    return True, None


def validate_name(value: str) -> Tuple[bool, Optional[str]]:
    """Name: should be 2+ words, no digits, not too long."""
    if not value or len(value.strip()) < 2:
        return False, "Name is too short."
    if any(ch.isdigit() for ch in value):
        return False, "Name should not contain digits."
    if len(value) > 100:
        return False, "Name exceeds maximum length."
    return True, None


def validate_dob(value: str) -> Tuple[bool, Optional[str]]:
    """
    DOB: accepts dd/mm/yyyy or dd-mm-yyyy.
    Does basic range checks (year 1900–current year).
    """
    match = re.match(r"^(\d{2})[/\-](\d{2})[/\-](\d{4})$", value)
    if not match:
        return False, f"DOB '{value}' is not in dd/mm/yyyy format."
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    current_year = datetime.now().year
    if not (1 <= day <= 31):
        return False, f"Invalid day: {day}."
    if not (1 <= month <= 12):
        return False, f"Invalid month: {month}."
    if not (1900 <= year <= current_year):
        return False, f"Year {year} is out of expected range (1900–{current_year})."
    return True, None


# ──────────────────────────────────────────────────────────────
# Composite validation result
# ──────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    valid: bool = True
    warnings: list = field(default_factory=list)

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        self.valid = False


# ──────────────────────────────────────────────────────────────
# Per-document-type composite validators
# ──────────────────────────────────────────────────────────────

def validate_aadhaar_fields(fields: dict) -> ValidationResult:
    """Validate all extracted Aadhaar fields."""
    result = ValidationResult()

    if "aadhaarNumber" in fields:
        ok, warn = validate_aadhaar_number(fields["aadhaarNumber"])
        if not ok:
            result.add_warning(f"Aadhaar Number: {warn}")
    else:
        result.add_warning("Aadhaar number could not be extracted.")

    if "name" in fields:
        ok, warn = validate_name(fields["name"])
        if not ok:
            result.add_warning(f"Name: {warn}")

    if "dob" in fields:
        ok, warn = validate_dob(fields["dob"])
        if not ok:
            result.add_warning(f"DOB: {warn}")

    logger.info(
        f"Aadhaar validation: valid={result.valid}, "
        f"warnings={len(result.warnings)}"
    )
    return result


def validate_pan_fields(fields: dict) -> ValidationResult:
    """Validate all extracted PAN fields."""
    result = ValidationResult()

    if "panNumber" in fields:
        ok, warn = validate_pan_number(fields["panNumber"])
        if not ok:
            result.add_warning(f"PAN Number: {warn}")
    else:
        result.add_warning("PAN number could not be extracted.")

    if "name" in fields:
        ok, warn = validate_name(fields["name"])
        if not ok:
            result.add_warning(f"Name: {warn}")

    if "dob" in fields:
        ok, warn = validate_dob(fields["dob"])
        if not ok:
            result.add_warning(f"DOB: {warn}")

    logger.info(
        f"PAN validation: valid={result.valid}, "
        f"warnings={len(result.warnings)}"
    )
    return result


def validate_satbara_fields(fields: dict) -> ValidationResult:
    """Validate extracted 7/12 Satbara fields."""
    result = ValidationResult()

    if "totalAreaHectares" in fields:
        try:
            val = float(fields["totalAreaHectares"])
            if val <= 0 or val > 1000:
                result.add_warning(f"Land area {val} Ha out of expected range (0-1000).")
        except ValueError:
            result.add_warning("Invalid land area number format.")
    else:
        result.add_warning("Land area in hectares could not be extracted.")

    if "gatNumber" not in fields:
        result.add_warning("Gat/Survey number could not be extracted.")

    logger.info(
        f"Satbara validation: valid={result.valid}, "
        f"warnings={len(result.warnings)}"
    )
    return result


# Document-type to validator mapping
_VALIDATORS = {
    "AADHAAR_FRONT": validate_aadhaar_fields,
    "AADHAAR_BACK": validate_aadhaar_fields,
    "PAN": validate_pan_fields,
    "SATBARA_7_12": validate_satbara_fields,
}


def validate_fields(document_type: str, fields: dict) -> ValidationResult:
    """
    Run the appropriate validator for a document type.
    Returns a ValidationResult with valid flag and list of warnings.
    """
    validator = _VALIDATORS.get(document_type)
    if validator is None:
        result = ValidationResult(valid=False)
        result.add_warning(f"No validator registered for document type: '{document_type}'")
        return result
    return validator(fields)
