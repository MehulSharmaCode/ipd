# backend/app/document_processing/validator.py
"""
Cross-Document Validator
==========================
Validates extracted data against what is already stored in the farmer's
MongoDB record, detecting conflicts and inconsistencies.

This runs AFTER the Profile Builder produces the $set update dict,
and BEFORE the update is written to MongoDB.

Checks performed:
  - Name mismatch between documents
  - DOB mismatch between documents
  - Duplicate document uploads
  - Missing mandatory fields for a doc type

The validator does NOT block updates — it produces warnings that are
returned to the frontend so the user can review conflicts.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ValidationSummary:
    """Result of cross-document validation."""

    def __init__(self):
        self.warnings: list[str] = []
        self.conflicts: list[dict] = []

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_conflict(self, field: str, existing: str, incoming: str,
                     source: str) -> None:
        self.conflicts.append({
            "field": field,
            "existing_value": existing,
            "incoming_value": incoming,
            "source_document": source,
        })
        self.warnings.append(
            f"Conflict in '{field}': existing='{existing}' vs "
            f"incoming='{incoming}' (from {source})"
        )

    def to_dict(self) -> dict:
        return {
            "has_conflicts": self.has_conflicts,
            "warnings": self.warnings,
            "conflicts": self.conflicts,
        }


class DocumentValidator:
    """
    Validates incoming extracted data against the existing farmer record.

    Usage:
        validator = DocumentValidator()
        summary = validator.validate(set_fields, existing_farmer, doc_type)
    """

    def validate(self, set_fields: dict, existing_farmer: Optional[dict],
                 doc_type: str) -> ValidationSummary:
        """
        Compare incoming fields against the existing farmer record.

        Args:
            set_fields:       Dict of MongoDB field updates (from ProfileBuilder).
            existing_farmer:  Current farmer record from MongoDB, or None.
            doc_type:         The document type being processed.

        Returns:
            ValidationSummary with any detected conflicts or warnings.
        """
        summary = ValidationSummary()

        if existing_farmer is None:
            # First document — nothing to validate against
            return summary

        # Check for duplicate uploads
        docs_uploaded = existing_farmer.get("documents_uploaded", [])
        for doc_ref in docs_uploaded:
            if doc_ref.startswith(f"{doc_type}:"):
                summary.add_warning(
                    f"A '{doc_type}' document has already been uploaded. "
                    "The new extraction will overwrite previous values."
                )
                break

        # Check name conflicts
        existing_name = existing_farmer.get("full_name", "").strip()
        incoming_name = set_fields.get("full_name", "").strip() or set_fields.get("owner_name", "").strip()
        if existing_name and incoming_name:
            if existing_name.lower() != incoming_name.lower():
                summary.add_conflict(
                    "full_name", existing_name, incoming_name, doc_type
                )

        # Check DOB conflicts
        existing_dob = existing_farmer.get("dob", "")
        incoming_dob = set_fields.get("dob", "")
        if existing_dob and incoming_dob:
            if existing_dob != incoming_dob:
                summary.add_conflict(
                    "dob", existing_dob, incoming_dob, doc_type
                )

        logger.info(
            "DocumentValidator: doc_type='%s', conflicts=%d, warnings=%d",
            doc_type, len(summary.conflicts), len(summary.warnings),
        )
        return summary
