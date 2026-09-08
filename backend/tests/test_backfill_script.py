"""
Unit tests for scripts/backfill_scheme_enrichment.py's pure/offline logic.
Network-touching behavior is validated via the live smoke tests described in
docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md Phase 6 (run manually, not in CI).
"""
from datetime import datetime

import pytest

from scripts.backfill_scheme_enrichment import (
    _no_source_documents,
    _process_one,
    selection_query,
)
from app.services.crawler.document_extractor import EXTRACTOR_VERSION


def test_selection_query_default_targets_incomplete_schemes():
    q = selection_query(force=False)
    conditions = q["$or"]
    assert {"required_documents": {"$exists": False}} in conditions
    assert any(
        c.get("required_documents.status", {}).get("$in") == ["fetch_failed", "not_fetched"]
        for c in conditions if "required_documents.status" in c
    )


def test_selection_query_force_is_empty_filter():
    assert selection_query(force=True) == {}


def test_no_source_documents_shape():
    rd = _no_source_documents(datetime(2026, 9, 8))
    assert rd["status"] == "unavailable"
    assert rd["source"] == "not_from_myscheme"
    assert rd["items"] == []
    assert rd["extractor_version"] == EXTRACTOR_VERSION


@pytest.mark.asyncio
async def test_process_one_scheme_without_slug_skips_http(fake_db):
    doc = {"_id": "x1", "myscheme_slug": None}
    fake_db["schemes"].docs.append(dict(doc))
    stats = {"documents_fetched": 0, "documents_missing": 0, "documents_failed": 0, "no_source": 0}
    await _process_one(fake_db, doc, fetcher=None, client=None, offline=False, dry_run=False, stats=stats)
    assert stats["no_source"] == 1
    updated = fake_db["schemes"].docs[0]
    assert updated["required_documents"]["status"] == "unavailable"
    assert updated["required_documents"]["source"] == "not_from_myscheme"


@pytest.mark.asyncio
async def test_process_one_offline_mode_no_client_needed(fake_db):
    doc = {
        "_id": "x2", "myscheme_slug": "some-scheme",
        "scheme_open_date_raw": "2019-02-24", "scheme_close_date_raw": None,
        "eligibility_raw": "", "benefits_raw": "",
        "source_url": "https://www.myscheme.gov.in/schemes/some-scheme",
    }
    fake_db["schemes"].docs.append(dict(doc))
    stats = {"documents_fetched": 0, "documents_missing": 0, "documents_failed": 0, "no_source": 0}
    await _process_one(fake_db, doc, fetcher=None, client=None, offline=True, dry_run=False, stats=stats)
    updated = fake_db["schemes"].docs[0]
    assert updated["application_timeline"]["status"] == "open_ended"
    assert updated["required_documents"]["status"] == "not_fetched"


@pytest.mark.asyncio
async def test_process_one_dry_run_writes_nothing(fake_db):
    doc = {"_id": "x3", "myscheme_slug": None}
    stats = {"documents_fetched": 0, "documents_missing": 0, "documents_failed": 0, "no_source": 0}
    await _process_one(fake_db, doc, fetcher=None, client=None, offline=False, dry_run=True, stats=stats)
    assert fake_db["schemes"].docs == []
    assert stats["no_source"] == 1


@pytest.mark.asyncio
async def test_process_one_manually_verified_offline_untouched(fake_db):
    preserved_rd = {"status": "available", "items": [{"raw_text": "X"}], "extractor_version": 1}
    preserved_tl = {"status": "window", "close_date_raw": "2099-01-01"}
    doc = {
        "_id": "x4", "myscheme_slug": "some-scheme", "manually_verified": True,
        "scheme_open_date_raw": None, "scheme_close_date_raw": None,
        "eligibility_raw": "", "benefits_raw": "",
        "required_documents": preserved_rd, "application_timeline": preserved_tl,
        "source_url": None,
    }
    fake_db["schemes"].docs.append(dict(doc))
    stats = {"documents_fetched": 0, "documents_missing": 0, "documents_failed": 0, "no_source": 0}
    await _process_one(fake_db, doc, fetcher=None, client=None, offline=True, dry_run=False, stats=stats)
    updated = fake_db["schemes"].docs[0]
    assert updated["required_documents"] == preserved_rd
    assert updated["application_timeline"] == preserved_tl
