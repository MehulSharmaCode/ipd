"""
Integration tests for the required-documents / application-timeline
enrichment wired into MySchemeIngestionScheduler.run_ingestion_cycle
(Phase 5 of docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md).

All myScheme HTTP calls are mocked with respx; MongoDB is replaced with the
FakeDB double from conftest.py.
"""
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from app.services.crawler.scheduler import MySchemeIngestionScheduler

PM_KISAN_OBJECT_ID = "62a70e86f038bd8499a6aa53"


def _search_response(fields: dict, es_id: str = "es-id-1", total: int = 1) -> dict:
    return {
        "status": "Success",
        "data": {
            "summary": {"total": total},
            "hits": {"items": [{"id": es_id, "fields": fields}]},
        },
    }


def _pm_kisan_search_fields() -> dict:
    return {
        "beneficiaryState": ["All"],
        "schemeShortTitle": "PM-KISAN",
        "level": "Central",
        "schemeFor": "Family",
        "nodalMinistryName": "Ministry Of Agriculture and Farmers Welfare",
        "schemeCategory": ["Agriculture,Rural & Environment"],
        "schemeName": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "slug": "pm-kisan",
        "briefDescription": "Income support scheme for farmers.",
        "tags": ["Farmers", "Agriculture"],
    }


def _mock_search_and_detail(sample_detail_payload):
    """Register the search + detail routes common to every test in this module."""
    respx.get(re_url_search()).mock(
        return_value=httpx.Response(200, json=_search_response(_pm_kisan_search_fields()))
    )
    respx.get(re_url_detail()).mock(
        return_value=httpx.Response(200, json=sample_detail_payload)
    )


def re_url_search():
    from app.core.config import settings
    return f"{settings.MYSCHEME_API_BASE.rstrip('/')}/search/v6/schemes"


def re_url_detail():
    from app.core.config import settings
    return f"{settings.MYSCHEME_API_BASE.rstrip('/')}/schemes/v6/public/schemes"


def re_url_documents(object_id: str):
    from app.core.config import settings
    return f"{settings.MYSCHEME_API_BASE.rstrip('/')}/schemes/v6/public/schemes/{object_id}/documents"


@pytest.mark.asyncio
async def test_fresh_scheme_inserted_with_both_sub_documents(
    fake_db, monkeypatch, sample_detail_payload, sample_documents_payload
):
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)

    with respx.mock:
        _mock_search_and_detail(sample_detail_payload)
        respx.get(re_url_documents(PM_KISAN_OBJECT_ID)).mock(
            return_value=httpx.Response(200, json=sample_documents_payload)
        )

        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=1)

    assert stats["errors"] == 0
    assert stats["new_schemes"] == 1
    assert stats["documents_fetched"] == 1

    docs = fake_db["schemes"].docs
    assert len(docs) == 1
    doc = docs[0]
    assert doc["required_documents"]["status"] == "available"
    assert doc["required_documents"]["item_count"] == 3
    assert doc["application_timeline"]["status"] == "open_ended"
    assert doc["myscheme_object_id"] == PM_KISAN_OBJECT_ID


@pytest.mark.asyncio
async def test_ingestion_idempotent_across_two_stale_cycles(
    fake_db, monkeypatch, sample_detail_payload, sample_documents_payload
):
    """Re-running ingestion (after artificially aging last_fetched past the
    staleness threshold, to force genuine re-processing rather than a
    freshness-skip) must produce byte-identical enrichment -- no duplication,
    no drift."""
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)

    with respx.mock:
        _mock_search_and_detail(sample_detail_payload)
        respx.get(re_url_documents(PM_KISAN_OBJECT_ID)).mock(
            return_value=httpx.Response(200, json=sample_documents_payload)
        )

        scheduler = MySchemeIngestionScheduler()
        stats1 = await scheduler.run_ingestion_cycle(limit=1)
        assert stats1["new_schemes"] == 1

        first_doc = dict(fake_db["schemes"].docs[0])

        # Force staleness so the second cycle actually re-fetches instead of
        # being skipped by the 24h freshness check.
        fake_db["schemes"].docs[0]["last_fetched"] = datetime.utcnow() - timedelta(hours=48)

        stats2 = await scheduler.run_ingestion_cycle(limit=1)

    assert stats2["updated_schemes"] == 1
    assert stats2["new_schemes"] == 0
    assert len(fake_db["schemes"].docs) == 1  # never duplicated

    second_doc = fake_db["schemes"].docs[0]
    assert second_doc["required_documents"]["items"] == first_doc["required_documents"]["items"]
    assert second_doc["application_timeline"]["status"] == first_doc["application_timeline"]["status"]
    assert second_doc["application_timeline"]["open_date_raw"] == first_doc["application_timeline"]["open_date_raw"]


@pytest.mark.asyncio
async def test_manually_verified_scheme_enrichment_untouched(
    fake_db, monkeypatch, sample_detail_payload, sample_documents_payload
):
    preserved_documents = {
        "status": "available", "source": "manual_review", "source_url": None,
        "fetched_at": None, "raw_markdown": None,
        "items": [{"raw_text": "Hand-verified doc", "display_name": "Hand-verified doc",
                    "doc_type": "UNKNOWN", "requirement": "mandatory",
                    "condition_text": None, "match_confidence": "none", "links": []}],
        "item_count": 1, "unmatched_count": 1, "extractor_version": 1,
    }
    preserved_timeline = {
        "status": "window", "open_date": None, "close_date": None,
        "open_date_raw": "2020-01-01", "close_date_raw": "2099-01-01",
        "open_date_source": None, "close_date_source": None,
        "application_modes": [], "text_mentions": [], "fetched_at": None,
        "extractor_version": 1,
    }
    fake_db["schemes"].docs.append({
        "_id": "existing-1",
        "scheme_id": "PM_KISAN",
        "myscheme_slug": "pm-kisan",
        "status": "published",
        "rules": [{"field": "land_size", "operator": "<=", "value": 2}],
        "benefit_calculation": {"type": "flat_rate", "base_rate": 6000},
        "manually_verified": True,
        "last_fetched": datetime.utcnow() - timedelta(hours=48),
        "content_hash": "old",
        "required_documents": preserved_documents,
        "application_timeline": preserved_timeline,
    })
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)

    with respx.mock:
        _mock_search_and_detail(sample_detail_payload)
        respx.get(re_url_documents(PM_KISAN_OBJECT_ID)).mock(
            return_value=httpx.Response(200, json=sample_documents_payload)
        )

        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=1)

    assert stats["updated_schemes"] == 1
    doc = fake_db["schemes"].docs[0]
    assert doc["required_documents"] == preserved_documents
    assert doc["application_timeline"] == preserved_timeline


@pytest.mark.asyncio
async def test_documents_fetch_failure_preserves_previous_available_data(
    fake_db, monkeypatch, sample_detail_payload
):
    previous_documents = {
        "status": "available", "source": "myscheme_documents_api",
        "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
        "fetched_at": None, "raw_markdown": "1. Aadhaar Card.\n",
        "items": [{"raw_text": "Aadhaar Card.", "display_name": "Aadhaar Card",
                    "doc_type": "AADHAAR", "requirement": "mandatory",
                    "condition_text": None, "match_confidence": "high", "links": []}],
        "item_count": 1, "unmatched_count": 0, "extractor_version": 1,
    }
    fake_db["schemes"].docs.append({
        "_id": "existing-2",
        "scheme_id": "PM_KISAN",
        "myscheme_slug": "pm-kisan",
        "status": "published",
        "rules": [{"field": "land_size", "operator": "<=", "value": 2}],
        "benefit_calculation": {"type": "flat_rate", "base_rate": 6000},
        "last_fetched": datetime.utcnow() - timedelta(hours=48),
        "content_hash": "old",
        "required_documents": previous_documents,
        "application_timeline": {"status": "unknown", "text_mentions": []},
    })
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)

    with respx.mock:
        _mock_search_and_detail(sample_detail_payload)
        respx.get(re_url_documents(PM_KISAN_OBJECT_ID)).mock(
            return_value=httpx.Response(500, json={"message": "error"})
        )

        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=1)

    assert stats["documents_failed"] == 1
    doc = fake_db["schemes"].docs[0]
    # The stale "fetch_failed" result must NOT have clobbered the good data.
    assert doc["required_documents"] == previous_documents


@pytest.mark.asyncio
async def test_search_api_failure_writes_no_partial_data(fake_db, monkeypatch):
    """
    A non-retryable search failure (e.g. 403) makes fetch_search_page return
    None; fetch_all_summaries treats that as "no summaries" rather than
    raising, so run_ingestion_cycle completes normally with an empty result
    -- this is pre-existing scheduler behavior (out of scope to change here).
    What this feature must guarantee is that a failed search writes NO
    scheme documents and still logs the run for observability.
    """
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)

    with respx.mock:
        respx.get(re_url_search()).mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )
        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=1)

    assert stats["summaries_fetched"] == 0
    assert fake_db["schemes"].docs == []
    assert len(fake_db["scheme_ingestion_log"].docs) == 1
