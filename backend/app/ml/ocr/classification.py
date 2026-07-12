"""
Document Classification Module
--------------------------------
Responsibility: Identify the type of an uploaded document from its raw OCR text.

Currently supports:
  - AADHAAR_FRONT  (with DOB, gender, Aadhaar number on front)
  - AADHAAR_BACK   (address side, usually no name)
  - PAN            (Income Tax PAN card)
  - UNKNOWN

Design: Adding a new document type requires only adding a new entry in
DOCUMENT_SIGNATURES and (optionally) a new ClassificationResult type string.
No other module needs to change.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Keyword signatures for each document type.
# Each entry is a dict with:
#   "type"     — canonical type string returned in the API
#   "keywords" — list of strings to look for in normalized text
#   "min_hits" — minimum keywords that must match
# ──────────────────────────────────────────────────────────────
DOCUMENT_SIGNATURES = [
    {
        "type": "AADHAAR_FRONT",
        "keywords": [
            "GOVERNMENT OF INDIA",
            "UNIQUE IDENTIFICATION",
            "UIDAI",
            "YOUR AADHAAR",
            "DOB",
            "DATE OF BIRTH",
            "YEAR OF BIRTH",
            "MALE",
            "FEMALE",
            "TRANSGENDER",
        ],
        "min_hits": 2,
    },
    {
        "type": "AADHAAR_BACK",
        "keywords": [
            "GOVERNMENT OF INDIA",
            "UNIQUE IDENTIFICATION",
            "UIDAI",
            "ADDRESS",
            "MOBILE",
            "PIN",
        ],
        "min_hits": 2,
    },
    {
        "type": "PAN",
        "keywords": [
            "INCOME TAX DEPARTMENT",
            "PERMANENT ACCOUNT NUMBER",
            "GOVT. OF INDIA",
            "GOVERNMENT OF INDIA",
            "FATHER",
            "INCOME TAX",
        ],
        "min_hits": 2,
    },
]


@dataclass
class ClassificationResult:
    document_type: str          # e.g. "AADHAAR_FRONT", "PAN", "UNKNOWN"
    confidence: float           # 0.0–1.0
    keyword_hits: int
    matched_keywords: list


def classify(raw_text: str) -> ClassificationResult:
    """
    Classify a document from its raw OCR text.

    Args:
        raw_text: The raw, uncleaned text from the OCR service.
    Returns:
        ClassificationResult with the detected document type.
    """
    normalized = raw_text.upper()
    best_match = None
    best_hits = 0

    for sig in DOCUMENT_SIGNATURES:
        matched = [kw for kw in sig["keywords"] if kw in normalized]
        hits = len(matched)
        if hits >= sig["min_hits"] and hits > best_hits:
            best_hits = hits
            best_match = sig
            best_keywords = matched

    if best_match is None:
        logger.warning("Document classification: UNKNOWN — no signatures matched")
        return ClassificationResult(
            document_type="UNKNOWN",
            confidence=0.0,
            keyword_hits=0,
            matched_keywords=[],
        )

    # Confidence: how many of the possible keywords were found
    total_keywords = len(best_match["keywords"])
    confidence = min(best_hits / total_keywords, 1.0)

    logger.info(
        f"Document classified as '{best_match['type']}' "
        f"({best_hits}/{total_keywords} keywords, confidence={confidence:.0%})"
    )

    return ClassificationResult(
        document_type=best_match["type"],
        confidence=confidence,
        keyword_hits=best_hits,
        matched_keywords=best_keywords,
    )


def is_aadhaar(result: ClassificationResult) -> bool:
    return result.document_type in {"AADHAAR_FRONT", "AADHAAR_BACK"}


def is_pan(result: ClassificationResult) -> bool:
    return result.document_type == "PAN"
