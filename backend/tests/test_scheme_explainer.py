"""
Unit tests for the evidence-based reasoning additions to SchemeExplainer
(build_match_signals, build_reason_summary, compute_reason_confidence).

These tests never assert on explain_eligible/explain_ineligible/_translate_rule
behavior changing -- those are untouched (see test_regression.py).
"""
import re

from app.ml.explainability.scheme_explainer import SchemeExplainer

REAL_STAND_UP_INDIA_PASSED_RULES = [
    {"field": "category", "operator": "==", "value": "SC", "farmer_value": "SC"},
    {"field": "occupation_type", "operator": "==", "value": "business_owner", "farmer_value": "business_owner"},
    {"field": "age", "operator": ">=", "value": 18, "farmer_value": 32},
]


def test_one_signal_per_passed_rule():
    signals = SchemeExplainer.build_match_signals(REAL_STAND_UP_INDIA_PASSED_RULES, "heuristic")
    assert len(signals) == 3
    for signal in signals:
        assert set(signal.keys()) == {
            "signal_type", "field", "operator", "scheme_value", "profile_value",
            "profile_field", "text", "evidence_source", "rule_provenance",
        }


def test_signal_type_mapping():
    signals = SchemeExplainer.build_match_signals(REAL_STAND_UP_INDIA_PASSED_RULES, "heuristic")
    by_field = {s["field"]: s["signal_type"] for s in signals}
    assert by_field["category"] == "social_category_match"
    assert by_field["occupation_type"] == "occupation_match"
    assert by_field["age"] == "age_within_range"


def test_income_signal_text_contains_both_amounts():
    rules = [{"field": "income", "operator": "<=", "value": 200000, "farmer_value": 120000}]
    signals = SchemeExplainer.build_match_signals(rules, "heuristic")
    text = signals[0]["text"]
    assert "1,20,000".replace(",", "") in text.replace(",", "").replace("₹", "") or "120000" in text.replace(",", "").replace("₹", "")
    assert "200000" in text.replace(",", "").replace("₹", "")


def test_empty_passed_rules_yields_no_signals():
    assert SchemeExplainer.build_match_signals([], "heuristic") == []
    assert SchemeExplainer.build_match_signals(None, "heuristic") == []


def test_reason_summary_empty_signals_uses_documented_sentence():
    summary = SchemeExplainer.build_reason_summary([])
    assert summary == SchemeExplainer.NO_SIGNAL_REASON


def test_reason_summary_five_signals_shows_three_plus_count():
    # Deliberately picked fields whose templates contain no internal commas,
    # so the top-level ", " separators inserted by build_reason_summary can
    # be counted unambiguously.
    rules = [
        {"field": "state", "operator": "==", "value": "Maharashtra", "farmer_value": "Maharashtra"},
        {"field": "income", "operator": "<=", "value": 200000, "farmer_value": 120000},
        {"field": "age", "operator": ">=", "value": 18, "farmer_value": 32},
        {"field": "land_size", "operator": "<=", "value": 2, "farmer_value": 1.5},
        {"field": "occupation_type", "operator": "==", "value": "farmer", "farmer_value": "farmer"},
    ]
    signals = SchemeExplainer.build_match_signals(rules, "heuristic")
    summary = SchemeExplainer.build_reason_summary(signals)
    assert summary.startswith("Recommended because")
    assert "(+2 more matching criteria)" in summary
    # 3 clauses joined -> exactly 1 top-level comma before the final "and".
    body = summary.split("Recommended because ")[1].split(" (+2")[0]
    assert body.count(", ") == 1
    assert body.count(" and ") == 1


def test_signal_priority_ordering_independent_of_input_order():
    rules = [
        {"field": "crop", "operator": "in", "value": ["wheat"], "farmer_value": ["wheat"]},
        {"field": "state", "operator": "==", "value": "Maharashtra", "farmer_value": "Maharashtra"},
        {"field": "income", "operator": "<=", "value": 200000, "farmer_value": 120000},
    ]
    signals = SchemeExplainer.build_match_signals(rules, "heuristic")
    summary = SchemeExplainer.build_reason_summary(signals)
    # state_match has the highest priority, so its clause must appear first
    # in the assembled sentence regardless of input order.
    assert summary.index("state") < summary.index("income")
    assert summary.index("state") < summary.index("crop")


def test_confidence_verified_for_manually_verified_scheme():
    conf = SchemeExplainer.compute_reason_confidence([], {"manually_verified": True})
    assert conf == "verified"


def test_confidence_low_for_heuristic_single_signal():
    signals = SchemeExplainer.build_match_signals(
        [{"field": "age", "operator": ">=", "value": 18, "farmer_value": 32}], "heuristic"
    )
    conf = SchemeExplainer.compute_reason_confidence(
        signals, {"extraction_method": "heuristic", "extraction_confidence": "low"}
    )
    assert conf == "low"


def test_confidence_high_requires_llm_or_high_extraction_confidence():
    signals = SchemeExplainer.build_match_signals(REAL_STAND_UP_INDIA_PASSED_RULES, "llm")
    conf = SchemeExplainer.compute_reason_confidence(
        signals, {"extraction_method": "llm", "extraction_confidence": "high"}
    )
    assert conf == "high"


def test_list_valued_profile_value_renders_as_comma_string_not_python_repr():
    rules = [{"field": "crop", "operator": "in", "value": ["wheat", "rice"], "farmer_value": ["wheat"]}]
    signals = SchemeExplainer.build_match_signals(rules, "heuristic")
    text = signals[0]["text"]
    assert "[" not in text and "]" not in text
    assert "'" not in text


def test_no_fabrication_every_number_in_text_traces_to_the_rule():
    """Anti-fabrication check (plan sec. K.22): every numeral appearing in a
    signal's text must also appear in that signal's scheme_value or
    profile_value."""
    rules = [
        {"field": "income", "operator": "<=", "value": 200000, "farmer_value": 120000},
        {"field": "age", "operator": ">=", "value": 18, "farmer_value": 32},
        {"field": "land_size", "operator": "<=", "value": 2, "farmer_value": 1.5},
    ]
    signals = SchemeExplainer.build_match_signals(rules, "heuristic")
    for s in signals:
        # \d+(?:\.\d+)? keeps a decimal like "1.5" as one token instead of
        # splitting it into "1" and "5".
        numbers_in_text = set(re.findall(r"\d+(?:\.\d+)?", s["text"].replace(",", "")))
        allowed = set()
        for v in (s["scheme_value"], s["profile_value"]):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                allowed.add(str(int(v)) if float(v).is_integer() else str(v))
        assert numbers_in_text <= allowed, f"Unexplained number in: {s['text']}"


def test_gender_and_disability_and_category_templates():
    rules = [
        {"field": "gender", "operator": "==", "value": "female", "farmer_value": "female"},
        {"field": "category", "operator": "==", "value": "SC", "farmer_value": "SC"},
        {"field": "is_differently_abled", "operator": "==", "value": True, "farmer_value": True},
    ]
    signals = SchemeExplainer.build_match_signals(rules, "heuristic")
    texts = {s["field"]: s["text"] for s in signals}
    assert "Female" in texts["gender"]
    assert "Sc" in texts["category"] or "SC" in texts["category"]
    assert "disability" in texts["is_differently_abled"].lower()
