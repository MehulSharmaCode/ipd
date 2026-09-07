# backend/app/document_processing/profile_builder.py
"""
Farmer Profile Builder
========================
Merges extracted data from any document type into a unified set of
MongoDB update fields for the FarmerProfile.

This is the ONLY module that decides which extracted fields map to
which database columns. Neither the upload endpoint nor the individual
processors should contain mapping logic.

Precedence policy:
  - Identity fields (aadhar_number, pan_number) come from their
    respective documents only.
  - Agricultural fields (land_area, crops, etc.) come from 7/12 only.
  - Common fields (full_name, district) use the most recent extraction
    unless a higher-confidence source already populated them.
"""

import logging
from typing import Optional

from app.document_processing.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class FarmerProfileBuilder:
    """
    Converts an ExtractionResult into a dict of MongoDB $set updates.

    Usage:
        builder = FarmerProfileBuilder()
        set_fields = builder.build_update(extraction_result)
        # set_fields is ready for: db["farmers"].update_one(..., {"$set": set_fields})
    """

    # Maps (doc_type, extracted_field_name) → MongoDB field name
    # Only fields listed here will be persisted.
    _FIELD_MAP = {
        # Aadhaar
        ("aadhar", "aadhar_number"):    "aadhar_number",
        ("aadhar", "full_name"):        "full_name",
        ("aadhar", "gender"):           "gender",
        ("aadhar", "dob"):              "dob",
        ("aadhar", "birth_year"):       "birth_year",

        # PAN
        ("pan", "pan_number"):          "pan_number",
        ("pan", "full_name"):           "full_name",
        ("pan", "father_name"):         "father_name",
        ("pan", "dob"):                 "dob",

        # 7/12 Satbara
        ("7_12", "owner_name"):         "owner_name",
        ("7_12", "survey_number"):      "survey_number",
        ("7_12", "gat_number"):         "gat_number",
        ("7_12", "village"):            "village",
        ("7_12", "taluka"):             "taluka",
        ("7_12", "district"):           "district",
        ("7_12", "land_area"):          "land_area",
        ("7_12", "current_crop"):       "current_crop",
        ("7_12", "irrigation"):         "irrigation_type",
        ("7_12", "soil_type"):          "soil_type",
        ("7_12", "ownership_type"):     "land_ownership",
        ("7_12", "co_owners"):          "co_owners",
        ("7_12", "land_use"):           "land_use",
        ("7_12", "season"):             "crop_season",
    }

    # Verification flags set when extraction is valid
    _VERIFICATION_FLAGS = {
        "aadhar":  "is_aadhar_verified",
        "aadhaar": "is_aadhar_verified",
        "pan":     "is_pan_verified",
        "7_12":    "is_7_12_verified",
    }

    def build_update(self, result: ExtractionResult) -> dict:
        """
        Build a flat dict of MongoDB $set fields from an ExtractionResult.

        Only fields that are:
          - present in _FIELD_MAP for this doc_type
          - non-None in the extraction result

        will be included. Returns an empty dict if the extraction failed.
        """
        if not result.success:
            logger.warning(
                "ProfileBuilder: skipping update — extraction failed "
                "for doc_type='%s': %s", result.document_type, result.error
            )
            return {}

        doc_type = result.document_type
        set_fields: dict = {}

        for extracted_name, ext_field in result.fields.items():
            if ext_field.value is None:
                continue
            db_key = self._FIELD_MAP.get((doc_type, extracted_name))
            if db_key:
                set_fields[db_key] = ext_field.value

        # ── Derived fields ──────────────────────────────────────────
        # land_area is stored as a formatted string (e.g. "6.11"); the
        # rules engine and ML pipeline key off the numeric hectares value.
        if "land_area" in set_fields:
            try:
                set_fields["land_size_hectares"] = float(set_fields["land_area"])
            except (TypeError, ValueError):
                logger.warning(
                    "ProfileBuilder: could not parse land_area=%r as float",
                    set_fields["land_area"],
                )

        # Satbara712Processor only handles Maharashtra 7/12 records — the
        # state is implied by the document type, even though Gemini's
        # extraction schema doesn't return it as a field.
        if doc_type == "7_12":
            set_fields["state"] = "Maharashtra"

        if "aadhar_number" in set_fields:
            clean_aadhar = str(set_fields["aadhar_number"]).replace(" ", "")
            set_fields["aadhar_last4"] = clean_aadhar[-4:]

        # Set verification flag if validation passed
        is_valid = result.validation.get("valid", False)
        if is_valid:
            flag = self._VERIFICATION_FLAGS.get(doc_type)
            if flag:
                set_fields[flag] = True

        logger.info(
            "ProfileBuilder: doc_type='%s' → %d fields to update: %s",
            doc_type, len(set_fields), list(set_fields.keys()),
        )
        return set_fields
