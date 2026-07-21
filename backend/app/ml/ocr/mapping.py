"""
Farmer Profile Mapping Module
------------------------------
Responsibility: Map extracted OCR fields to the FarmerProfile database schema.

This is the bridge between raw OCR output and the structured farmer record.
Each document type maps to a specific subset of profile fields.

Design principle: OCR assists registration — it does NOT replace user verification.
All mapped values are suggestions; users can edit everything before submission.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _normalize_gender(gender: Optional[str]) -> Optional[str]:
    """Normalize gender strings to the values expected by the FarmerProfile model."""
    if not gender:
        return None
    g = gender.strip().upper()
    mapping = {
        "MALE": "Male",
        "FEMALE": "Female",
        "TRANSGENDER": "Other",
        "OTHER": "Other",
    }
    return mapping.get(g)


def _parse_year_to_age(birth_year: Optional[str]) -> Optional[int]:
    """Estimate age from birth year using the current calendar year."""
    if not birth_year:
        return None
    try:
        year = int(birth_year)
        age = datetime.now().year - year
        if 5 <= age <= 120:
            return age
    except (ValueError, TypeError):
        pass
    return None


def map_aadhaar_to_profile(fields: dict) -> dict:
    """
    Map Aadhaar-extracted fields to farmer profile fields.

    Aadhaar Front provides:
      name → full_name (if profile name is empty)
      dob  → (stored as reference for age calculation)
      birthYear → age (estimated)
      gender → gender
      aadhaarNumber → aadhar_number (masked in logs)
    """
    profile_update = {}

    if fields.get("name"):
        profile_update["full_name_ocr_suggestion"] = fields["name"]

    if fields.get("aadhaarNumber"):
        profile_update["aadhar_number"] = fields["aadhaarNumber"]
        # Log only last 4 digits
        masked = "XXXX XXXX " + fields["aadhaarNumber"].replace(" ", "")[-4:]
        logger.info(f"Mapping Aadhaar number: {masked}")

    if fields.get("gender"):
        normalized = _normalize_gender(fields["gender"])
        if normalized:
            profile_update["gender"] = normalized

    if fields.get("birthYear"):
        age = _parse_year_to_age(fields["birthYear"])
        if age:
            profile_update["age"] = age

    if fields.get("dob"):
        profile_update["dob"] = fields["dob"]

    logger.info(f"Aadhaar→Profile mapping: {list(profile_update.keys())}")
    return profile_update


def map_pan_to_profile(fields: dict) -> dict:
    """
    Map PAN-extracted fields to farmer profile fields.

    PAN provides:
      name → full_name (if profile name is empty)
      panNumber → pan_number (masked in logs)
      dob → dob
    """
    profile_update = {}

    if fields.get("name"):
        profile_update["full_name_ocr_suggestion"] = fields["name"]

    if fields.get("panNumber"):
        profile_update["pan_number"] = fields["panNumber"]
        # Log only first 5 chars (non-sensitive alphabetic part)
        masked = fields["panNumber"][:5] + "XXXXX"
        logger.info(f"Mapping PAN number: {masked}")

    if fields.get("dob"):
        profile_update["dob"] = fields["dob"]

    logger.info(f"PAN→Profile mapping: {list(profile_update.keys())}")
    return profile_update


# Document-type to mapper function
_MAPPERS = {
    "AADHAAR_FRONT": map_aadhaar_to_profile,
    "AADHAAR_BACK": map_aadhaar_to_profile,
    "PAN": map_pan_to_profile,
}


def map_to_profile(document_type: str, fields: dict) -> dict:
    """
    Map extracted OCR fields to farmer profile fields for the given document type.

    Args:
        document_type: Classified document type (e.g., "AADHAAR_FRONT", "PAN").
        fields: Extracted fields dict from the appropriate parser.
    Returns:
        Dict of profile field suggestions to auto-fill on the frontend form.
    """
    mapper = _MAPPERS.get(document_type)
    if mapper is None:
        logger.warning(f"No profile mapper for document type: '{document_type}'")
        return {}
    return mapper(fields)
