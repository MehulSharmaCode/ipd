"""
Regression tests proving the pre-existing eligibility/explanation/ranking
behavior is byte-identical to before this feature (docs/SCHEME_REQUIREMENTS_
FEATURE_PLAN.md Part IV Phase 10). Nothing in RulesEngine, SchemeExplainer's
original methods, or MySchemeNormalizer's original keys may have changed.
"""
from app.ml.rules.rules_engine import RulesEngine
from app.ml.explainability.scheme_explainer import SchemeExplainer
from app.services.crawler.normalizer import MySchemeNormalizer
from app.services.crawler.parser import MySchemeParser

GOLDEN_SCHEME = {
    "scheme_id": "PM_KISAN",
    "name": "PM-KISAN",
    "status": "published",
    "rules": [
        {"field": "income", "operator": "<=", "value": 200000},
        {"field": "land_size", "operator": "<=", "value": 2},
        {"field": "farmer_type", "operator": "in", "value": ["small", "medium"]},
    ],
}

GOLDEN_PROFILE = {
    "income": 120000,
    "land_size": 1.5,
    "farmer_type": "small",
    "state": "maharashtra",
}


def test_rules_engine_check_scheme_output_unchanged():
    engine = RulesEngine(rules_path=None)
    result = engine.check_scheme(GOLDEN_SCHEME, GOLDEN_PROFILE)

    assert result["is_eligible"] is True
    assert len(result["passed_rules"]) == 3
    assert result["failed_rules"] == []
    # Exact golden shape of one passed rule -- untouched by this feature.
    income_rule = next(r for r in result["passed_rules"] if r["field"] == "income")
    assert income_rule == {
        "field": "income", "operator": "<=", "value": 200000, "farmer_value": 120000,
    }


def test_rules_engine_ineligible_scheme_unchanged():
    engine = RulesEngine(rules_path=None)
    profile = dict(GOLDEN_PROFILE, income=500000)
    result = engine.check_scheme(GOLDEN_SCHEME, profile)
    assert result["is_eligible"] is False
    assert len(result["failed_rules"]) == 1
    assert result["failed_rules"][0]["field"] == "income"


def test_explain_eligible_string_format_unchanged():
    passed_rules = [
        {"field": "income", "operator": "<=", "value": 200000, "farmer_value": 120000},
    ]
    explanation = SchemeExplainer.explain_eligible(passed_rules)
    assert explanation == ["Matches: Annual Income: ₹200,000"]


def test_explain_ineligible_string_format_unchanged():
    failed_rules = [
        {"field": "income", "operator": "<=", "value": 200000, "farmer_value": 500000},
    ]
    explanation = SchemeExplainer.explain_ineligible(failed_rules)
    assert explanation == [
        "Not eligible: Requires Annual Income = ₹200,000, but your profile has 500000"
    ]


def test_explain_eligible_empty_rules_unchanged():
    assert SchemeExplainer.explain_eligible([]) == [
        "You met all general eligibility criteria for this scheme."
    ]


def test_normalizer_still_produces_every_pre_existing_key():
    """Enrichment fields are additive -- every field the normalizer produced
    before this feature must still be present."""
    parsed_record = {
        "slug": "pm-kisan", "scheme_name": "PM-KISAN", "level": "central",
        "ministry": "Ministry Of Agriculture", "categories": ["Agriculture,Rural & Environment"],
        "tags": ["Farmers"], "beneficiary_states": ["All"],
        "brief_description": "desc", "close_date": None,
        "scheme_open_date": "2019-02-24", "myscheme_object_id": "abc123",
        "eligibility_description_md": "eligibility text", "benefits_md": "benefits text",
    }
    normalized = MySchemeNormalizer().normalize(parsed_record)

    pre_existing_keys = {
        "scheme_id", "name", "rules", "conflicts_with", "benefit_calculation",
        "department", "description", "category", "level", "state", "benefit_type",
        "status", "source_url", "myscheme_slug", "myscheme_tags",
        "eligibility_raw", "benefits_raw", "last_fetched", "content_hash", "updated_at",
    }
    assert pre_existing_keys <= normalized.keys()
    assert normalized["scheme_id"] == "PM_KISAN"
    assert normalized["level"] == "central"


def test_parse_summary_output_keys_unchanged():
    fields = {
        "_id": "es1", "slug": "pm-kisan", "schemeName": "PM-KISAN",
        "schemeShortTitle": "PMK", "level": "Central",
        "nodalMinistryName": "Ministry", "schemeCategory": ["Agriculture"],
        "tags": ["Farmers"], "beneficiaryState": ["All"],
        "briefDescription": "desc", "schemeCloseDate": None,
    }
    parsed = MySchemeParser.parse_summary(fields)
    pre_existing_keys = {
        "myscheme_id", "slug", "scheme_name", "short_title", "level", "ministry",
        "categories", "tags", "beneficiary_states", "brief_description", "close_date",
    }
    assert set(parsed.keys()) == pre_existing_keys


def test_scheme_projection_covers_every_field_ranking_reads():
    """Explicit field-name assertion (not eyeball) that
    app.api.farmers.SCHEME_PROJECTION includes every field actually read by
    the ranking path: RulesEngine, SchemeSuccessPredictor, BenefitPredictor,
    SchemeKnowledgeGraph, SchemeRankingEngine, SchemeExplainer."""
    from app.api.farmers import SCHEME_PROJECTION

    required_by_ranking_path = {
        "_id", "scheme_id", "name", "department", "description", "category",
        "level", "state", "benefit_type", "benefit_calculation", "conflicts_with",
        "rules", "status", "source_url", "myscheme_slug", "financial_benefit",
        "manually_verified", "extraction_method", "extraction_confidence",
        "required_documents", "application_timeline",
    }
    assert required_by_ranking_path <= SCHEME_PROJECTION.keys()
    # And the two largest, unused-in-ranking fields are deliberately excluded.
    assert "eligibility_raw" not in SCHEME_PROJECTION
    assert "benefits_raw" not in SCHEME_PROJECTION
