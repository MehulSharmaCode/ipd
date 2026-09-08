"""
Unit tests for app.services.crawler.document_extractor.

Fixtures are verbatim myScheme.gov.in payload captures (see conftest.py).
"""
from datetime import datetime, timezone

from app.services.crawler.document_extractor import (
    build_required_documents,
    flatten_documents_ast,
    normalize_document_line,
    parse_documents_markdown,
)

NOW = datetime(2026, 9, 8, 9, 14, 22, tzinfo=timezone.utc)


def test_pm_kisan_produces_three_mandatory_items(sample_documents_payload):
    rd = build_required_documents(
        sample_documents_payload,
        source_url="https://www.myscheme.gov.in/schemes/pm-kisan",
        fetched_at=NOW,
    )
    assert rd["status"] == "available"
    assert rd["item_count"] == 3
    doc_types = [i["doc_type"] for i in rd["items"]]
    assert doc_types == ["AADHAAR", "LAND_RECORD", "BANK_ACCOUNT"]
    assert all(i["requirement"] == "mandatory" for i in rd["items"])


def test_ast_only_payload_same_item_count(sample_documents_payload_ast_only):
    rd = build_required_documents(
        sample_documents_payload_ast_only, source_url=None, fetched_at=NOW
    )
    assert rd["status"] == "available"
    assert rd["item_count"] == 3


def test_markdown_only_payload_parses_items():
    payload = {
        "status": "Success",
        "data": {
            "en": {
                "documents_required": [],
                "documentsRequired_md": "\n1. Aadhaar Card.\n1. PAN Card.\n\n<br>\n\n",
            }
        },
    }
    rd = build_required_documents(payload, source_url=None, fetched_at=NOW)
    assert rd["status"] == "available"
    assert rd["item_count"] == 2
    assert rd["items"][0]["doc_type"] == "AADHAAR"
    assert rd["items"][1]["doc_type"] == "PAN"


def test_null_data_is_unavailable(sample_documents_payload_empty):
    rd = build_required_documents(
        sample_documents_payload_empty, source_url=None, fetched_at=NOW
    )
    assert rd["status"] == "unavailable"
    assert rd["items"] == []


def test_fetch_failed_status():
    rd = build_required_documents(
        None, source_url=None, fetched_at=NOW, fetch_failed=True
    )
    assert rd["status"] == "fetch_failed"
    assert rd["items"] == []


def test_conditional_phrase_detected():
    entry = normalize_document_line("Caste Certificate (If applicable)")
    assert entry["requirement"] == "conditional"
    assert entry["condition_text"] == "If applicable"
    assert entry["display_name"] == "Caste Certificate"


def test_markdown_link_extracted_into_links():
    entry = normalize_document_line(
        "[Undertaking](https://x.gov.in/y.pdf)"
    )
    assert entry["raw_text"] == "Undertaking"
    assert entry["links"] == ["https://x.gov.in/y.pdf"]


def test_double_escaped_html_entities():
    entry = normalize_document_line("Applicant&amp;amp;#39;s photo")
    assert "Applicant's photo" in entry["raw_text"]


def test_runon_markdown_produces_two_items():
    items = parse_documents_markdown(
        "1. [A](http://x/1)1. [B](http://x/2)"
    )
    assert len(items) == 2


def test_duplicate_lines_are_deduplicated():
    payload = {
        "status": "Success",
        "data": {
            "en": {
                "documents_required": [],
                "documentsRequired_md": "1. Aadhaar Card.\n1. Aadhaar Card.\n1. PAN Card.\n",
            }
        },
    }
    rd = build_required_documents(payload, source_url=None, fetched_at=NOW)
    assert rd["item_count"] == 2


def test_non_http_link_is_dropped():
    entry = normalize_document_line("[Form](javascript:alert(1))")
    assert entry["links"] == []


def test_idempotent(sample_documents_payload):
    rd1 = build_required_documents(
        sample_documents_payload, source_url="u", fetched_at=NOW
    )
    rd2 = build_required_documents(
        sample_documents_payload, source_url="u", fetched_at=NOW
    )
    assert rd1 == rd2


def test_runon_gpt_hbocwwb_full_fixture(sample_documents_payload_runon):
    rd = build_required_documents(
        sample_documents_payload_runon, source_url=None, fetched_at=NOW
    )
    assert rd["status"] == "available"
    assert rd["item_count"] == 10
    undertaking = rd["items"][2]
    assert undertaking["display_name"] == "Undertaking"
    assert undertaking["links"] == [
        "https://storage.hrylabour.gov.in/uploads_new_2/bocw/scheme_undertaking/1628746916.pdf"
    ]
    work_slip = rd["items"][3]
    assert work_slip["display_name"] == "Work Slip"
    assert work_slip["doc_type"] == "UNKNOWN"
    caste = [i for i in rd["items"] if i["doc_type"] == "CASTE_CERTIFICATE"][0]
    assert caste["requirement"] == "conditional"
    assert caste["condition_text"] == "If applicable"


def test_flatten_documents_ast_handles_nested_children():
    nodes = [
        {
            "type": "ol_list",
            "children": [
                {"type": "list_item", "children": [{"text": "Aadhaar Card."}]},
                {"type": "paragraph", "children": [{"text": ""}]},
            ],
        }
    ]
    assert flatten_documents_ast(nodes) == ["Aadhaar Card."]


def test_flatten_documents_ast_empty_input():
    assert flatten_documents_ast(None) == []
    assert flatten_documents_ast([]) == []


def test_normalize_document_line_too_short_returns_none():
    assert normalize_document_line("NA") is None
    assert normalize_document_line("") is None
    assert normalize_document_line("   ") is None


def test_item_cap_at_forty():
    md = "\n".join(f"1. Document type {i}" for i in range(60))
    payload = {"status": "Success", "data": {"en": {"documents_required": [], "documentsRequired_md": md}}}
    rd = build_required_documents(payload, source_url=None, fetched_at=NOW)
    assert len(rd["items"]) == 40
    assert rd["item_count"] == 60
