"""
Unit tests for app.services.crawler.document_taxonomy.

All sample strings are verbatim document-requirement lines observed on
myScheme.gov.in during the live audit (2026-09-08).
"""
from app.services.crawler.document_taxonomy import classify_document, UNKNOWN_DOC_TYPE


def test_aadhaar_high_confidence():
    assert classify_document("Aadhaar Card.") == ("AADHAAR", "high")


def test_land_record_plural_high_confidence():
    # "papers" (plural) must still be a high-confidence word-boundary match,
    # not merely a loose substring of "paper".
    assert classify_document("Landholding papers.") == ("LAND_RECORD", "high")


def test_bank_account_high_confidence():
    assert classify_document("Savings Bank Account.") == ("BANK_ACCOUNT", "high")


def test_conditional_phrase_does_not_prevent_classification():
    doc_type, confidence = classify_document(
        "Scheduled Tribe Certificate for APST patients"
    )
    assert doc_type == "CASTE_CERTIFICATE"
    assert confidence == "high"


def test_unknown_document_stays_unknown():
    doc_type, confidence = classify_document(
        "Some entirely novel state-specific form XYZ-9"
    )
    assert doc_type == UNKNOWN_DOC_TYPE
    assert confidence == "none"


def test_unmatched_generic_lines_are_unknown_not_guessed():
    # These must NOT be fuzzily mapped onto some plausible-looking type.
    assert classify_document("Farmer details.")[0] == UNKNOWN_DOC_TYPE
    assert classify_document("Any other documents as required.")[0] == UNKNOWN_DOC_TYPE


def test_longest_alias_wins_income_tax_return_not_income_certificate():
    doc_type, confidence = classify_document("Income Tax Return")
    assert doc_type == "INCOME_TAX_RETURN"
    assert confidence == "high"


def test_longest_alias_wins_embedded_in_sentence():
    doc_type, _ = classify_document("Previous two year's income tax return")
    assert doc_type == "INCOME_TAX_RETURN"


def test_plain_income_certificate_still_classified():
    doc_type, confidence = classify_document("Copy of Income Certificate (Original)")
    assert doc_type == "INCOME_CERTIFICATE"
    assert confidence == "high"


def test_empty_string_is_unknown():
    assert classify_document("") == (UNKNOWN_DOC_TYPE, "none")


def test_no_fuzzy_matching_short_novel_token():
    # A short random token must not accidentally substring-match a real alias.
    doc_type, confidence = classify_document("XYZ Form 27B")
    assert doc_type == UNKNOWN_DOC_TYPE
    assert confidence == "none"
