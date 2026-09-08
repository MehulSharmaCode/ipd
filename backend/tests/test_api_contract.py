"""
Tests for the Phase 8 API contract changes:
  - SchemeRecommendation retains the new evidence/enrichment fields
    (this is the direct regression test for PRE-5: FastAPI's response_model
    used to silently strip any field not declared on the Pydantic model).
  - GET /api/schemes/{scheme_id}/requirements returns the documented shape.

The requirements-endpoint tests mount only app.api.schemes.router on a bare
FastAPI app (no lifespan, no real Mongo connection) and monkeypatch get_db()
to return the FakeDB double from conftest.py -- this avoids needing a live
database or starting the background ingestion loop just to test one route.
"""
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.farmer import SchemeBundle, SchemeRecommendation

NOW = datetime(2026, 9, 8, tzinfo=timezone.utc)


def test_scheme_recommendation_retains_new_fields_pre5_regression():
    payload = {
        "scheme_id": "PM_KISAN",
        "scheme_name": "PM-KISAN",
        "success_probability": 0.8,
        "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
        "match_signals": [{
            "signal_type": "state_match", "field": "state", "operator": "==",
            "scheme_value": "Maharashtra", "profile_value": "Maharashtra",
            "profile_field": "state", "text": "Your state matches.",
        }],
        "reason_summary": "Recommended because your state matches.",
        "reason_confidence": "medium",
        "required_documents": {
            "status": "available",
            "items": [{"raw_text": "Aadhaar Card.", "display_name": "Aadhaar Card", "doc_type": "AADHAAR"}],
            "item_count": 1,
        },
        "application_timeline": {"status": "open_ended", "open_date_raw": "2019-02-24"},
        "timeline_state": {"state": "open_ended", "label": "Open"},
    }
    rec = SchemeRecommendation.model_validate(payload)
    dumped = rec.model_dump()

    for key in ("source_url", "match_signals", "reason_summary", "reason_confidence",
                "required_documents", "application_timeline", "timeline_state"):
        assert key in dumped, f"{key} was stripped by the model -- PRE-5 regressed"

    assert dumped["source_url"] == "https://www.myscheme.gov.in/schemes/pm-kisan"
    assert dumped["required_documents"]["item_count"] == 1
    assert dumped["match_signals"][0]["signal_type"] == "state_match"


def test_old_shaped_payload_still_validates_with_defaults():
    """Backward compatibility: a response built before this feature (just the
    original 7 fields) must still validate, with sensible defaults for the
    new fields."""
    old_payload = {
        "scheme_id": "X", "scheme_name": "Y", "success_probability": 0.5,
        "explanation": ["Matches: State: Maharashtra"],
        "predicted_financial_value": 6000, "benefit_type": "Cash",
        "prediction_explanation": "Flat rate.",
    }
    rec = SchemeRecommendation.model_validate(old_payload)
    dumped = rec.model_dump()
    assert dumped["source_url"] is None
    assert dumped["match_signals"] == []
    assert dumped["reason_summary"] == ""
    assert dumped["reason_confidence"] == "low"
    assert dumped["required_documents"] is None
    assert dumped["application_timeline"] is None


def test_scheme_bundle_schemes_carry_new_fields():
    bundle = SchemeBundle.model_validate({
        "bundle_id": "BUNDLE_01",
        "schemes": [{
            "scheme_id": "X", "scheme_name": "Y", "success_probability": 0.5,
            "source_url": "https://www.myscheme.gov.in/schemes/x",
            "reason_summary": "Recommended because your age meets the minimum.",
        }],
    })
    assert bundle.schemes[0].source_url == "https://www.myscheme.gov.in/schemes/x"
    assert bundle.schemes[0].reason_summary.startswith("Recommended because")


# --- GET /api/schemes/{scheme_id}/requirements --------------------------------

def _build_test_app(monkeypatch, fake_db):
    from app.api import schemes as schemes_module
    monkeypatch.setattr(schemes_module, "get_db", lambda: fake_db)
    app = FastAPI()
    app.include_router(schemes_module.router)
    return app


def test_requirements_endpoint_returns_documented_shape(monkeypatch, fake_db):
    scheme_object_id = ObjectId()
    fake_db["schemes"].docs.append({
        "_id": scheme_object_id,
        "scheme_id": "PM_KISAN",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
        "last_fetched": NOW,
        "required_documents": {
            "status": "available", "source": "myscheme_documents_api",
            "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
            "fetched_at": NOW, "raw_markdown": "1. Aadhaar Card.\n",
            "items": [{"raw_text": "Aadhaar Card.", "display_name": "Aadhaar Card",
                       "doc_type": "AADHAAR", "requirement": "mandatory",
                       "condition_text": None, "match_confidence": "high", "links": []}],
            "item_count": 1, "unmatched_count": 0, "extractor_version": 1,
        },
        "application_timeline": {
            "status": "open_ended", "open_date": NOW, "close_date": None,
            "open_date_raw": "2019-02-24", "close_date_raw": None,
            "open_date_source": "myscheme_basic_details.schemeOpenDate",
            "close_date_source": None, "application_modes": [], "text_mentions": [],
            "fetched_at": NOW, "extractor_version": 1,
        },
    })

    app = _build_test_app(monkeypatch, fake_db)
    with TestClient(app) as client:
        resp = client.get("/api/schemes/PM_KISAN/requirements")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["scheme_id"] == "PM_KISAN"
    # raw_markdown IS present here (unlike the /farmers/me response) -- this
    # is the full audit record.
    assert "Aadhaar Card" in body["required_documents"]["raw_markdown"]
    assert body["required_documents"]["item_count"] == 1
    assert body["application_timeline"]["status"] == "open_ended"
    assert body["timeline_state"]["state"] == "open_ended"


def test_requirements_endpoint_unknown_scheme_404(monkeypatch, fake_db):
    app = _build_test_app(monkeypatch, fake_db)
    with TestClient(app) as client:
        resp = client.get("/api/schemes/DOES_NOT_EXIST/requirements")
    assert resp.status_code == 404


def test_requirements_endpoint_unenriched_scheme_returns_200_not_fetched(monkeypatch, fake_db):
    fake_db["schemes"].docs.append({
        "_id": ObjectId(), "scheme_id": "OLD_SCHEME", "name": "An old scheme",
        "source_url": None, "last_fetched": None,
    })
    app = _build_test_app(monkeypatch, fake_db)
    with TestClient(app) as client:
        resp = client.get("/api/schemes/OLD_SCHEME/requirements")

    assert resp.status_code == 200
    body = resp.json()
    assert body["required_documents"]["status"] == "not_fetched"
    assert body["application_timeline"]["status"] == "unknown"
    assert body["timeline_state"]["state"] == "unknown"
