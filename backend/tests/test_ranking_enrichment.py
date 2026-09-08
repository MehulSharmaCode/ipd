"""
Verifies that SchemeRankingEngine.rank_schemes() attaches the new evidence/
enrichment fields to eligible schemes and NEVER to ineligible schemes
(docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sec. 7b / Definition of Done #12-13).
"""
from datetime import datetime, timezone

import pytest

from app.ml.inference.ranking_engine import SchemeRankingEngine

NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)

REQUIRED_DOCUMENTS = {
    "status": "available", "source": "myscheme_documents_api",
    "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
    "fetched_at": NOW, "raw_markdown": "1. Aadhaar Card.\n",
    "items": [{"raw_text": "Aadhaar Card.", "display_name": "Aadhaar Card",
               "doc_type": "AADHAAR", "requirement": "mandatory",
               "condition_text": None, "match_confidence": "high", "links": []}],
    "item_count": 1, "unmatched_count": 0, "extractor_version": 1,
}

APPLICATION_TIMELINE = {
    "status": "open_ended", "open_date": NOW, "close_date": None,
    "open_date_raw": "2019-02-24", "close_date_raw": None,
    "open_date_source": "myscheme_basic_details.schemeOpenDate", "close_date_source": None,
    "application_modes": [], "text_mentions": [], "fetched_at": NOW, "extractor_version": 1,
}


def _eligible_scheme():
    return {
        "scheme_id": "TEST_ELIGIBLE_SCHEME",
        "name": "Test Eligible Scheme",
        "department": "Test Dept",
        "description": "A test scheme",
        "category": "Agriculture,Rural & Environment",
        "level": "central",
        "state": None,
        "benefit_type": "Cash",
        "benefit_calculation": {"type": "flat_rate", "base_rate": 6000},
        "conflicts_with": [],
        "rules": [{"field": "age", "operator": ">=", "value": 18}],
        "status": "published",
        "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
        "myscheme_slug": "pm-kisan",
        "extraction_method": "heuristic",
        "extraction_confidence": "medium",
        "manually_verified": False,
        "required_documents": REQUIRED_DOCUMENTS,
        "application_timeline": APPLICATION_TIMELINE,
    }


def _ineligible_scheme():
    return {
        "scheme_id": "TEST_INELIGIBLE_SCHEME",
        "name": "Test Ineligible Scheme",
        "department": "Test Dept",
        "description": "A test scheme requiring an age no farmer profile here meets",
        "category": "Agriculture,Rural & Environment",
        "level": "central",
        "state": None,
        "benefit_type": "Cash",
        "benefit_calculation": {"type": "flat_rate", "base_rate": 6000},
        "conflicts_with": [],
        "rules": [{"field": "age", "operator": ">=", "value": 90}],
        "status": "published",
        "source_url": "https://www.myscheme.gov.in/schemes/some-other-scheme",
        "myscheme_slug": "some-other-scheme",
        "extraction_method": "heuristic",
        "extraction_confidence": "medium",
        "manually_verified": False,
        "required_documents": REQUIRED_DOCUMENTS,
        "application_timeline": APPLICATION_TIMELINE,
    }


ENRICHMENT_KEYS = {
    "match_signals", "reason_summary", "reason_confidence",
    "required_documents", "application_timeline", "timeline_state",
}


@pytest.fixture(scope="module")
def engine():
    return SchemeRankingEngine()


def test_eligible_scheme_carries_all_enrichment_fields(engine):
    farmer_profile = {
        "age": 32, "state": "Maharashtra", "annual_income": 120000,
        "land_size_hectares": 1.5, "primary_crops": ["wheat"], "gender": "male",
    }
    result = engine.rank_schemes(farmer_profile, dynamic_schemes=[_eligible_scheme()])
    ranked = result["ranked_schemes"]
    assert len(ranked) == 1
    scheme = ranked[0]
    assert ENRICHMENT_KEYS <= scheme.keys()
    assert scheme["required_documents"]["status"] == "available"
    assert "raw_markdown" not in scheme["required_documents"]  # stripped by _public_documents
    assert scheme["reason_summary"].startswith("Recommended because")
    assert len(scheme["match_signals"]) >= 1
    assert scheme["timeline_state"]["state"] == "open_ended"


def test_ineligible_scheme_never_carries_enrichment_fields(engine):
    farmer_profile = {
        "age": 32, "state": "Maharashtra", "annual_income": 120000,
        "land_size_hectares": 1.5, "primary_crops": ["wheat"], "gender": "male",
    }
    result = engine.rank_schemes(
        farmer_profile, dynamic_schemes=[_eligible_scheme(), _ineligible_scheme()]
    )
    ineligible = result["ineligible_schemes"]
    assert any(s["scheme_id"] == "TEST_INELIGIBLE_SCHEME" for s in ineligible)
    for scheme in ineligible:
        assert not (ENRICHMENT_KEYS & scheme.keys()), (
            f"Ineligible scheme {scheme.get('scheme_id')} unexpectedly carries "
            f"enrichment fields: {ENRICHMENT_KEYS & scheme.keys()}"
        )


def test_match_signals_capped_at_six(engine):
    scheme = _eligible_scheme()
    scheme["rules"] = [
        {"field": "age", "operator": ">=", "value": 18},
        {"field": "state", "operator": "==", "value": "maharashtra"},
        {"field": "income", "operator": "<=", "value": 500000},
        {"field": "land_size", "operator": "<=", "value": 5},
        {"field": "gender", "operator": "==", "value": "male"},
        {"field": "category", "operator": "in", "value": ["general", "obc"]},
        {"field": "farmer_type", "operator": "in", "value": ["small", "medium"]},
        {"field": "crop", "operator": "in", "value": ["wheat"]},
    ]
    farmer_profile = {
        "age": 32, "state": "maharashtra", "annual_income": 120000,
        "land_size_hectares": 1.5, "primary_crops": ["wheat"], "gender": "male",
        "category": "general", "farmer_type": "small",
    }
    result = engine.rank_schemes(farmer_profile, dynamic_schemes=[scheme])
    ranked = result["ranked_schemes"]
    assert len(ranked) == 1
    assert len(ranked[0]["match_signals"]) <= 6
