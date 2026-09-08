"""
Tests for the fetcher.py / parser.py changes made for the required-documents
and application-timeline enrichment feature (Phase 4).
"""
import httpx
import pytest
import respx

from app.services.crawler.fetcher import MySchemeApiFetcher
from app.services.crawler.parser import MySchemeParser


def test_parse_detail_extracts_myscheme_object_id(sample_detail_payload):
    parsed = MySchemeParser.parse_detail(sample_detail_payload)
    assert parsed["myscheme_object_id"] == "62a70e86f038bd8499a6aa53"


def test_parse_detail_extracts_application_modes(sample_detail_payload):
    parsed = MySchemeParser.parse_detail(sample_detail_payload)
    modes = parsed["application_modes"]
    assert len(modes) == 2
    assert modes[0]["mode"] == "Online"
    assert modes[0]["url"] == "https://pmkisan.gov.in/RegistrationFormnew.aspx"
    assert modes[1]["mode"] == "Online - via CSC"
    assert modes[1]["url"] is None


def test_parse_detail_preserves_scheme_open_date(sample_detail_payload):
    parsed = MySchemeParser.parse_detail(sample_detail_payload)
    assert parsed["scheme_open_date"] == "2019-02-24"


def test_parse_detail_handles_empty_payload_without_keyerror():
    parsed = MySchemeParser.parse_detail({})
    assert parsed["myscheme_object_id"] is None
    assert parsed["application_modes"] == []
    assert parsed["scheme_open_date"] is None


def test_parse_summary_extracts_close_date(sample_search_item):
    parsed = MySchemeParser.parse_summary(sample_search_item["fields"])
    assert parsed["close_date"] == "2025-03-31"
    assert parsed["slug"] == "sui"


def test_parse_documents_null_data_returns_none():
    assert MySchemeParser.parse_documents({"status": "Success", "data": None}) is None
    assert MySchemeParser.parse_documents(None) is None
    assert MySchemeParser.parse_documents({}) is None


def test_parse_documents_extracts_md_and_ast(sample_documents_payload):
    parsed = MySchemeParser.parse_documents(sample_documents_payload)
    assert parsed is not None
    assert "Aadhaar Card" in parsed["documentsRequired_md"]
    assert len(parsed["documents_required"]) == 2


@pytest.mark.asyncio
async def test_fetch_scheme_documents_hits_correct_endpoint(sample_documents_payload):
    fetcher = MySchemeApiFetcher()

    with respx.mock:
        route = respx.get(
            f"{fetcher.base_url}/schemes/v6/public/schemes/62a70e86f038bd8499a6aa53/documents",
            params={"lang": "en"},
        ).mock(return_value=httpx.Response(200, json=sample_documents_payload))

        async with httpx.AsyncClient(headers=fetcher._build_headers()) as client:
            result = await fetcher.fetch_scheme_documents(client, "62a70e86f038bd8499a6aa53")

        assert route.called
        assert result == sample_documents_payload


@pytest.mark.asyncio
async def test_fetch_scheme_documents_returns_none_on_500():
    fetcher = MySchemeApiFetcher()
    with respx.mock:
        respx.get(
            f"{fetcher.base_url}/schemes/v6/public/schemes/badid/documents"
        ).mock(return_value=httpx.Response(500, json={"message": "error"}))

        async with httpx.AsyncClient(headers=fetcher._build_headers()) as client:
            result = await fetcher.fetch_scheme_documents(client, "badid")

        assert result is None


@pytest.mark.asyncio
async def test_fetch_scheme_documents_none_object_id_short_circuits():
    fetcher = MySchemeApiFetcher()
    with respx.mock:
        async with httpx.AsyncClient(headers=fetcher._build_headers()) as client:
            result = await fetcher.fetch_scheme_documents(client, "")
        assert result is None
