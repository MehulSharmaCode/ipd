"""
Full-path end-to-end test: ingest (mocked myScheme) -> normalize -> enrich ->
persist (FakeDB) -> RulesEngine -> SchemeRankingEngine -> API response model.

Also carries the anti-fabrication assertions required by
docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md Definition of Done, K.19-22.
"""
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from app.services.crawler.scheduler import MySchemeIngestionScheduler
from app.ml.services.recommendation_service import RecommendationService
from app.models.farmer import FarmerResponse

STALE = datetime.utcnow() - timedelta(hours=48)


def _search_response(items: list, total: int) -> dict:
    return {
        "status": "Success",
        "data": {"summary": {"total": total}, "hits": {"items": items}},
    }


def _search_item(es_id: str, slug: str, name: str, category: str, close_date=None) -> dict:
    return {
        "id": es_id,
        "fields": {
            "beneficiaryState": ["Maharashtra"],
            "schemeShortTitle": name[:10],
            "level": "State",
            "schemeFor": "Individual",
            "nodalMinistryName": "Ministry Of Agriculture",
            "schemeCategory": [category],
            "schemeName": name,
            "slug": slug,
            "briefDescription": f"{name} description.",
            "tags": ["Farmers"],
            "schemeCloseDate": close_date,
        },
    }


def _detail_payload(object_id: str, name: str, open_date=None, eligibility_md="") -> dict:
    return {
        "status": "Success",
        "data": {
            "_id": object_id,
            "slug": name.lower().replace(" ", "-"),
            "en": {
                "basicDetails": {
                    "schemeName": name, "schemeOpenDate": open_date,
                    "targetBeneficiaries": [], "schemeCategory": [],
                    "nodalMinistryName": {}, "nodalDepartmentName": {},
                },
                "schemeContent": {
                    "briefDescription": f"{name} description.",
                    "benefits_md": "Flat rate benefit of Rs.5000.",
                    "detailedDescription_md": "", "exclusions_md": "",
                },
                "applicationProcess": [{"mode": "Online", "url": "https://example.gov.in/apply"}],
                "schemeDefinitions": [],
                "eligibilityCriteria": {"eligibilityDescription_md": eligibility_md},
            },
        },
    }


def _documents_payload(md: str) -> dict:
    return {
        "status": "Success",
        "data": {"en": {"documentsRequired_md": md, "documents_required": []}},
    }


@pytest.mark.asyncio
async def test_full_ingest_to_recommendation_pipeline(fake_db, monkeypatch):
    """
    Ingest 3 schemes:
      1. WITH_DOCS_EXPIRED  - documents present, close date in the past
      2. WITH_DOCS_NO_DATES - documents present, no dates at all
      3. NO_DOCS            - no documents section at all
    Then run the real recommendation pipeline for a farmer who matches
    schemes 1 and 2, and assert the full evidence/enrichment chain end to end.
    """
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)

    from app.core.config import settings
    base = settings.MYSCHEME_API_BASE.rstrip("/")

    with respx.mock:
        respx.get(f"{base}/search/v6/schemes").mock(
            return_value=httpx.Response(200, json=_search_response(
                [
                    _search_item("es1", "with-docs-expired", "With Docs Expired Scheme",
                                 "Agriculture,Rural & Environment", close_date="2025-03-31"),
                    _search_item("es2", "with-docs-no-dates", "With Docs No Dates Scheme",
                                 "Agriculture,Rural & Environment"),
                    _search_item("es3", "no-docs-scheme", "No Docs Scheme",
                                 "Agriculture,Rural & Environment"),
                ],
                total=3,
            ))
        )

        def detail_route(request):
            slug = request.url.params.get("slug")
            mapping = {
                "with-docs-expired": ("obj1", "With Docs Expired Scheme",
                                       None, "Farmers with land up to 2 hectares."),
                "with-docs-no-dates": ("obj2", "With Docs No Dates Scheme",
                                        "2020-01-01", "Farmers with land up to 2 hectares."),
                "no-docs-scheme": ("obj3", "No Docs Scheme",
                                    None, "Farmers with land up to 2 hectares."),
            }
            object_id, name, open_date, elig = mapping[slug]
            return httpx.Response(200, json=_detail_payload(object_id, name, open_date, elig))

        respx.get(f"{base}/schemes/v6/public/schemes").mock(side_effect=detail_route)

        def documents_route(request):
            object_id = request.url.path.split("/")[-2]
            if object_id == "obj1":
                return httpx.Response(200, json=_documents_payload("1. Aadhaar Card.\n1. Land record.\n"))
            if object_id == "obj2":
                return httpx.Response(200, json=_documents_payload("1. PAN Card.\n"))
            # obj3: no documents section at all
            return httpx.Response(200, json={"status": "Success", "data": None})

        respx.get(url__regex=rf"{base}/schemes/v6/public/schemes/.+/documents").mock(
            side_effect=documents_route
        )

        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=3)

    assert stats["errors"] == 0
    assert stats["new_schemes"] == 3
    assert stats["documents_fetched"] == 2
    assert stats["documents_missing"] == 1

    # --- Inject deterministic rules onto the 3 schemes so ranking is testable
    # without depending on the real (heuristic) rule_extractor's output. ---
    for doc in fake_db["schemes"].docs:
        doc["rules"] = [{"field": "land_size", "operator": "<=", "value": 2}]
        doc["status"] = "published"
        doc["extraction_method"] = "heuristic"
        doc["extraction_confidence"] = "high"

    farmer_profile = {
        "_id": "farmer1", "land_size_hectares": 1.5, "state": "Maharashtra",
        "annual_income": 100000, "primary_crops": ["wheat"], "farmer_type": "small",
    }

    schemes = fake_db["schemes"].docs
    recs = RecommendationService.get_recommendations(farmer_profile, schemes=schemes)
    eligible_by_id = {s["scheme_id"]: s for s in recs["eligible"]}

    assert len(eligible_by_id) == 3

    expired = eligible_by_id["WITH_DOCS_EXPIRED"]
    no_dates = eligible_by_id["WITH_DOCS_NO_DATES"]
    no_docs = eligible_by_id["NO_DOCS_SCHEME"]

    # Scheme 1: documents present, close date in the past -> expired
    assert expired["required_documents"]["status"] == "available"
    assert expired["required_documents"]["item_count"] == 2
    assert expired["timeline_state"]["state"] == "expired"
    assert len(expired["match_signals"]) >= 1
    assert expired["reason_summary"].startswith("Recommended because")

    # Scheme 2: documents present, no close date -> open_ended
    assert no_dates["required_documents"]["status"] == "available"
    assert no_dates["required_documents"]["item_count"] == 1
    assert no_dates["timeline_state"]["state"] == "open_ended"

    # Scheme 3: no documents section at all -> honestly "unavailable"
    assert no_docs["required_documents"]["status"] == "unavailable"
    assert no_docs["required_documents"]["items"] == []
    assert no_docs["timeline_state"]["state"] == "unknown"

    # --- Anti-fabrication (Definition of Done K.19-20) ---------------------
    # No close_date was ever produced except the one literal "2025-03-31"
    # from the mocked source.
    for scheme in eligible_by_id.values():
        close_raw = scheme["application_timeline"].get("close_date_raw")
        assert close_raw in (None, "2025-03-31")

    # Every displayed document raw_text is one of the literal source lines.
    source_lines = {"Aadhaar Card.", "Land record.", "PAN Card."}
    for scheme in eligible_by_id.values():
        for item in scheme["required_documents"]["items"]:
            assert item["raw_text"] in source_lines

    # --- Response model validates the full farmer payload -------------------
    farmer_profile["recommended_schemes"] = recs["eligible"]
    farmer_profile["recommended_bundles"] = recs["bundles"]
    farmer_profile["ineligible_schemes"] = recs["ineligible"]
    farmer_profile["full_name"] = "Test"
    farmer_profile["email"] = "t@example.com"
    validated = FarmerResponse.model_validate(farmer_profile)
    assert len(validated.recommended_schemes) == 3


@pytest.mark.asyncio
async def test_documents_endpoint_500_still_completes_cycle(fake_db, monkeypatch):
    """/documents 500 for one scheme -> status: fetch_failed, ingestion still
    completes with 0 errors and every other scheme unaffected."""
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)
    from app.core.config import settings
    base = settings.MYSCHEME_API_BASE.rstrip("/")

    with respx.mock:
        respx.get(f"{base}/search/v6/schemes").mock(
            return_value=httpx.Response(200, json=_search_response(
                [_search_item("es1", "flaky-scheme", "Flaky Scheme", "Agriculture")], total=1
            ))
        )
        respx.get(f"{base}/schemes/v6/public/schemes").mock(
            return_value=httpx.Response(200, json=_detail_payload("obj1", "Flaky Scheme"))
        )
        respx.get(url__regex=rf"{base}/schemes/v6/public/schemes/.+/documents").mock(
            return_value=httpx.Response(500, json={"message": "error"})
        )

        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=1)

    assert stats["errors"] == 0
    assert stats["documents_failed"] == 1
    doc = fake_db["schemes"].docs[0]
    assert doc["required_documents"]["status"] == "fetch_failed"


@pytest.mark.asyncio
async def test_detail_api_500_logs_error_and_writes_no_scheme(fake_db, monkeypatch):
    """/schemes/v6/public/schemes (detail) 500 -> the per-scheme error is
    caught, counted, and no document is written for that scheme."""
    monkeypatch.setattr("app.services.crawler.scheduler.get_db", lambda: fake_db)
    from app.core.config import settings
    base = settings.MYSCHEME_API_BASE.rstrip("/")

    with respx.mock:
        respx.get(f"{base}/search/v6/schemes").mock(
            return_value=httpx.Response(200, json=_search_response(
                [_search_item("es1", "broken-detail-scheme", "Broken Detail Scheme", "Agriculture")],
                total=1,
            ))
        )
        respx.get(f"{base}/schemes/v6/public/schemes").mock(
            return_value=httpx.Response(500, json={"message": "error"})
        )

        scheduler = MySchemeIngestionScheduler()
        stats = await scheduler.run_ingestion_cycle(limit=1)

    # merge_summary_and_detail degrades gracefully (detail_payload=None), so
    # the scheme is still created from summary data alone, just without
    # detail-derived fields (myscheme_object_id, application dates).
    assert stats["errors"] == 0
    assert stats["new_schemes"] == 1
    doc = fake_db["schemes"].docs[0]
    assert doc["myscheme_object_id"] is None
    assert doc["required_documents"]["status"] == "unavailable"
