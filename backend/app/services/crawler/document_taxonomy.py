"""
Document Requirement Taxonomy
==============================
Canonical document types + alias vocabulary for classifying the free-text
document requirement lines published by myScheme.gov.in.

Mirrors the design of app/document_processing/normalizer.py:
  Canonical -> {"aliases": [...]}
Unmatched values are left unchanged and typed UNKNOWN.
No fuzzy matching. No LLM. No hallucination.

This is a closed vocabulary, not scheme-specific data — it must never contain
a scheme name, slug, or a document list scoped to one particular scheme.
"""

import re
from typing import Dict, List, Tuple

DOCUMENT_SPEC: Dict[str, Dict[str, List[str]]] = {
    "AADHAAR": {"aliases": ["aadhaar card", "aadhar card", "aadhaar", "aadhar",
                             "aadhaar number", "aadhaar details", "uid card"]},
    "PAN": {"aliases": ["pan card", "pan number", "permanent account number"]},
    "VOTER_ID": {"aliases": ["voter id", "voter card", "voter identity card",
                              "epic card", "election card"]},
    "IDENTITY_PROOF": {"aliases": ["identity proof", "proof of identity", "id proof",
                                    "photo identification", "government-issued photo"]},
    "ADDRESS_PROOF": {"aliases": ["address proof", "proof of address", "proof of residence",
                                   "residence proof", "residential certificate",
                                   "residence certificate"]},
    "DOMICILE_CERTIFICATE": {"aliases": ["domicile certificate", "permanent resident certificate",
                                          "indigenous inhabitant certificate",
                                          "sikkim subject certificate",
                                          "certificate of identification"]},
    "RATION_CARD": {"aliases": ["ration card", "barcoded ration card"]},
    "INCOME_CERTIFICATE": {"aliases": ["income certificate", "income proof",
                                        "proof of income", "salary certificate"]},
    "INCOME_TAX_RETURN": {"aliases": ["income tax return", "itr", "tax return"]},
    "CASTE_CERTIFICATE": {"aliases": ["caste certificate", "scheduled caste certificate",
                                       "scheduled tribe certificate", "st certificate",
                                       "sc certificate", "obc certificate",
                                       "community certificate"]},
    "BIRTH_CERTIFICATE": {"aliases": ["birth certificate"]},
    "AGE_PROOF": {"aliases": ["age proof", "proof of age", "date of birth certificate"]},
    "DISABILITY_CERTIFICATE": {"aliases": ["disability certificate", "divyang certificate",
                                            "handicap certificate", "udid card"]},
    "BANK_ACCOUNT": {"aliases": ["bank account", "bank passbook", "passbook",
                                  "savings bank account", "cancelled cheque",
                                  "bank account details", "bank statement"]},
    "LAND_RECORD": {"aliases": ["landholding papers", "landholding paper",
                                 "land ownership document", "land ownership documents",
                                 "7/12", "satbara", "8-a record", "khasra",
                                 "proof of agricultural land", "land record",
                                 "proof of land", "lease agreement"]},
    "EDUCATION_CERTIFICATE": {"aliases": ["mark sheet", "marksheet", "matriculation certificate",
                                           "school leaving certificate", "passing certificate",
                                           "degree certificate", "educational certificate",
                                           "proof of admission", "course structure"]},
    "PHOTOGRAPH": {"aliases": ["passport size photo", "passport-size photograph",
                                "photograph", "photo"]},
    "SIGNATURE": {"aliases": ["signature"]},
    "MOBILE_NUMBER": {"aliases": ["mobile number", "mobile no"]},
    "EMAIL": {"aliases": ["email id", "e-mail id", "email address"]},
    "MEDICAL_CERTIFICATE": {"aliases": ["medical certificate", "doctor's certificate",
                                         "doctors certificate", "health certificate"]},
    "REGISTRATION_CERTIFICATE": {"aliases": ["registration certificate", "registration card",
                                              "worker registration card", "registration proof",
                                              "kisan credit card", "kcc"]},
    "UNDERTAKING": {"aliases": ["undertaking", "affidavit", "self-declaration",
                                 "self declaration", "self-certificate"]},
    "APPLICATION_FORM": {"aliases": ["application form", "common application form",
                                      "filled application"]},
    "PROJECT_REPORT": {"aliases": ["project report", "detailed project report", "dpr"]},
}

UNKNOWN_DOC_TYPE = "UNKNOWN"
TAXONOMY_VERSION = 1

# Built once at import time: (alias, doc_type) sorted by alias length descending
# so the longest, most specific alias is tried first (e.g. "income tax return"
# before "income certificate" would ever get a chance to loose-match it).
_ALIAS_TABLE: List[Tuple[str, str]] = sorted(
    (
        (alias, doc_type)
        for doc_type, spec in DOCUMENT_SPEC.items()
        for alias in spec["aliases"]
    ),
    key=lambda pair: len(pair[0]),
    reverse=True,
)


def classify_document(text: str) -> Tuple[str, str]:
    """
    Classify a free-text document requirement line into a canonical doc_type.

    Returns (doc_type, match_confidence):
      - ("<TYPE>", "high") - alias matched at a word boundary
      - ("<TYPE>", "low")  - alias matched only as a loose substring
      - ("UNKNOWN", "none") - no alias matched at all

    Longest alias wins; the first high-confidence match is returned immediately,
    otherwise the first low-confidence match found is returned as a fallback.
    No fuzzy matching, no edit distance, no LLM.
    """
    if not text:
        return UNKNOWN_DOC_TYPE, "none"

    lowered = text.lower()
    low_match: Tuple[str, str] | None = None

    for alias, doc_type in _ALIAS_TABLE:
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return doc_type, "high"
        if low_match is None and alias in lowered:
            low_match = (doc_type, "low")

    if low_match is not None:
        return low_match

    return UNKNOWN_DOC_TYPE, "none"
