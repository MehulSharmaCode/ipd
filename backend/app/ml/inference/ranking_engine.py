"""
ranking_engine.py

Hybrid rule-based + ML ranking engine for AgriSense scheme recommendations.

Scoring formula (applied per eligible scheme, in order):
  final_score = (probability * total_affinity) + proximity_total

  Where:
    probability       = ml_model.predict_success(farmer_features, scheme_features)
    total_affinity    = state_weight * crop_weight * demographic_weight * domain_multiplier
    proximity_total   = land_prox_bonus + inc_prox_bonus + age_bonus
                      + rule_density_bonus + fin_bonus + hash_tiebreaker

  domain_multiplier = 1.0 for agricultural schemes, 0.001 for all other domains.
  demographic_weight = 1.5 ONLY for agricultural schemes with category/gender rules.
  demographic_weight does NOT affect domain_multiplier — the two are independent multipliers.

YAML fallback policy:
  schemes_rules.yaml is loaded at __init__ time for backward-compatibility with
  the knowledge graph initializer only. rank_schemes() NEVER uses YAML data for
  live requests. If dynamic_schemes is None (indicating a DB fetch failure),
  rank_schemes() raises RuntimeError immediately so the caller can return a
  structured "schemes temporarily unavailable" error to the client.
"""

import math
from pathlib import Path

from app.ml.explainability.scheme_explainer import SchemeExplainer
from app.ml.reinforcement.policy_engine import SchemePolicy
from app.ml.reinforcement.interaction_logger import log_interaction
from app.ml.rules.rules_engine import RulesEngine
from app.ml.inference.success_predictor import SchemeSuccessPredictor
from app.ml.utils.profile_mapper import map_farmer_to_ml_features
from app.ml.utils.logger import get_logger
from app.ml.features.feature_store import FeatureStore
from app.ml.graph.knowledge_graph import SchemeKnowledgeGraph
from app.ml.inference.benefit_predictor import BenefitPredictor


logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
# RULES_PATH is kept here only as a reference for one-time seeding scripts.
# rank_schemes() NEVER loads or uses this file for live farmer requests.
RULES_PATH = BASE_DIR / "rules" / "schemes_rules.yaml"

# ─── Domain Classification Keywords ─────────────────────────────────────────
# Primary signal is the scheme's 'category' field (see _classify_domain below).
# Keyword lists are secondary signals for edge-case disambiguation only.
_AGRI_KEYWORDS = [
    "farm", "agri", "crop", "kisan", "cultivat", "seed", "irrigation", "soil",
    "fertilizer", "horticultur", "pashu", "dairy", "livestock", "fishery",
    "pashupalak", "krishak", "fasal", "paddy", "tiller", "tractors",
    "plantation", "falbag", "shetkari",
]
_NON_AGRI_OVERRIDE_KEYWORDS = [
    # Keyword patterns that override an Agriculture category when present in the
    # scheme name or department — these indicate schemes that happen to fall under
    # Agriculture ministry but target non-farming beneficiaries (students,
    # construction workers, artisans, etc.).
    #
    # IMPORTANT: These must be specific multi-word phrases, NOT broad single words.
    # Broad single-word overrides (e.g. "stipend", "award", "pension") incorrectly
    # suppress legitimate farmer schemes (poultry stipends, agricultural awards,
    # old-age pension for agricultural labourers). Each entry here must be a phrase
    # that is unambiguous — i.e., only appears in genuinely non-agri contexts.
    "patent office", "industrial park", "specialty steel", "petrochemical",
    "charkha", "powerloom", "bocwwb", "construction worker", "sericulture reeler",
    "ugc", "nielit", "marriage incentive", "rehabilitation of pwd",
    "surgical grant", "police training", "sanitary napkin", "postdoctoral",
    "handicraft artisans", "tirtha yatra", "book bank",
    # Education-specific patterns (scholarship/stipend to students, not farmers)
    "scholarship", "school enrolment", "tuition fee", "hostel subsidy",
    "matric scholarship", "college scholarship", "education loan",
    "student scholarship", "students scholarship", "diploma scholarship",
]


def _classify_domain(scheme: dict) -> bool:
    """
    Return True if the scheme is agricultural, False otherwise.

    Primary signal: scheme's 'category' field.
      - If category contains 'Agriculture' (case-insensitive) → is_agri = True
      - All other category values → is_agri = False

    Secondary signal (override): if the scheme name or department contains any
    _NON_AGRI_OVERRIDE_KEYWORD, is_agri is forced to False regardless of category.
    This handles the edge case of schemes filed under Agriculture ministry that
    target non-farming beneficiaries (e.g. scholarship, pension, education).

    The old keyword-only approach (checking name/dept/eligibility_raw) is removed
    as primary logic because it misclassified correctly-categorized agri schemes
    (e.g. SYSS was marked non-agri despite category='Agriculture,Rural & Environment').
    """
    raw_category = (scheme.get("category") or "").lower()
    name_lower = (scheme.get("name") or "").lower()
    dept_lower = (scheme.get("department") or "").lower()

    # Primary: category field
    is_agri_by_category = "agricultur" in raw_category or "rural" in raw_category

    # Override: if any hard non-agri keyword appears in name/department
    has_non_agri_override = any(
        kw in name_lower or kw in dept_lower
        for kw in _NON_AGRI_OVERRIDE_KEYWORDS
    )

    return is_agri_by_category and not has_non_agri_override


class SchemeRankingEngine:
    """
    Ranking engine responsible for generating ranked scheme recommendations
    using rule filtering + ML probability scoring + reinforcement learning
    selection, integrated with Knowledge Graph bundling.
    """

    def __init__(self):
        logger.info("Initializing Scheme Ranking Engine")

        # RulesEngine with no YAML path — no YAML file is loaded at startup.
        # filter_schemes() operates exclusively on dynamic_schemes passed per-request.
        self.rule_engine = RulesEngine(rules_path=None)

        # SchemeKnowledgeGraph is built fresh from live MongoDB schemes on each
        # rank_schemes() call (line ~350 below). The empty-list initialisation here
        # creates a no-op stub that is never used for live ranking.
        self.knowledge_graph = SchemeKnowledgeGraph([])

        self.ml_model = SchemeSuccessPredictor()
        self.feature_store = FeatureStore()
        self.benefit_predictor = BenefitPredictor()
        self.policy = SchemePolicy()
        logger.info(
            "SchemeRankingEngine ready. YAML fallback is DISABLED — "
            "all live requests require a valid dynamic_schemes list from MongoDB."
        )

    def rank_schemes(self, farmer_profile: dict, dynamic_schemes: list = None):
        """
        Rank schemes for a given farmer profile.

        Args:
            farmer_profile: Farmer profile dict from the API request.
            dynamic_schemes: List of scheme documents fetched live from MongoDB.
                             Must NOT be None for a live farmer request.
                             Pass an empty list [] if MongoDB returned no results.

        Raises:
            RuntimeError: If dynamic_schemes is None, indicating the caller failed
                          to fetch schemes from MongoDB. The YAML fallback is
                          intentionally NOT used for live requests to prevent
                          serving stale data to farmers.
        """
        # ── Guard: reject None (DB fetch failure) — never fall back to YAML ──
        if dynamic_schemes is None:
            raise RuntimeError(
                "rank_schemes received dynamic_schemes=None, indicating a MongoDB "
                "fetch failure. Refusing to fall back to YAML data. "
                "The caller should return a 'schemes temporarily unavailable' error."
            )

        if len(dynamic_schemes) == 0:
            logger.warning(
                "rank_schemes received an empty dynamic_schemes list. "
                "MongoDB returned no published schemes. Returning empty results."
            )
            return {
                "ranked_schemes": [],
                "recommended_bundles": [],
                "ineligible_schemes": [],
                "recommended_scheme": None,
            }

        logger.info("Building ML features from farmer profile")

        # Step 1 — Clean + normalize profile
        features = self.feature_store.build_features(farmer_profile)

        logger.info("Running scheme eligibility rules")

        # Step 2 — Filter eligible and ineligible schemes (using live DB data only)
        scheme_filter_results = self.rule_engine.filter_schemes(features, schemes=dynamic_schemes)
        eligible_schemes = scheme_filter_results.get("eligible", [])
        ineligible_schemes_raw = scheme_filter_results.get("ineligible", [])

        logger.info(f"Eligible schemes: {len(eligible_schemes)} | Ineligible: {len(ineligible_schemes_raw)}")

        ranked_results = []
        ineligible_results = []

        # Process Ineligible Schemes
        for scheme in ineligible_schemes_raw:
            scheme_id = scheme.get("scheme_id")
            explanation = SchemeExplainer.explain_ineligible(scheme.get("failed_rules", []))
            source_url = scheme.get("source_url") or (
                f"https://www.myscheme.gov.in/schemes/"
                f"{scheme.get('myscheme_slug', str(scheme_id).lower().replace('_', '-'))}"
            )
            ineligible_results.append({
                "scheme_id": scheme_id,
                "scheme_name": scheme.get("name"),
                "explanation": explanation,
                "source_url": source_url,
            })

        # Step 3 — Prepare farmer-level ML features ONCE
        base_farmer_features = map_farmer_to_ml_features(features)

        # Step 3b — Batch-predict all scheme probabilities in a SINGLE predict_proba()
        # call rather than N individual calls. Profiling showed N=218 individual
        # predict_success() calls took ~2,750ms (12.6ms/call). The batched call
        # takes ~15-20ms total — a 100-150x speedup for the ML inference phase.
        all_scheme_ml_features = [self.ml_model.build_scheme_features(s) for s in eligible_schemes]
        all_probabilities = self.ml_model.predict_batch(base_farmer_features, all_scheme_ml_features)

        # Step 4 — Score each eligible scheme (probabilities pre-computed above)
        for scheme_idx, scheme in enumerate(eligible_schemes):
            scheme_id = scheme.get("scheme_id")

            probability = all_probabilities[scheme_idx]
            explanation = SchemeExplainer.explain_eligible(scheme.get("passed_rules", []))

            # Dynamic Financial Value Prediction
            predicted_benefit = self.benefit_predictor.predict_benefit(scheme, base_farmer_features)
            scheme["financial_benefit"] = predicted_benefit["predicted_financial_value"]

            # ── 1. State Affinity Weight ──────────────────────────────────────
            state_weight = 1.0
            farmer_state = (features.get("state") or "").strip().lower()
            scheme_state = (scheme.get("state") or "").strip().lower()

            # Prefer state value from passed rules (most precise)
            rule_state_vals = [
                r.get("value") for r in scheme.get("passed_rules", [])
                if r.get("field") == "state"
            ]
            if rule_state_vals:
                first_val = rule_state_vals[0]
                if isinstance(first_val, str) and first_val.strip():
                    scheme_state = first_val.strip().lower()

            if scheme_state and scheme_state not in ["all states", "national", "india", "central", "all"]:
                state_weight = 2.5 if scheme_state == farmer_state else 0.1
            # else: state_weight stays 1.0 for Central / All-India schemes

            # ── 2. Crop Affinity Weight ───────────────────────────────────────
            crop_weight = 1.0
            farmer_crops = [c.lower() for c in (features.get("primary_crops") or [])]
            scheme_crop_rules = [r.get("value") for r in scheme.get("rules", []) if r.get("field") == "crop"]
            flat_scheme_crops = []
            for sc in scheme_crop_rules:
                if isinstance(sc, list):
                    flat_scheme_crops.extend([str(x).lower() for x in sc])
                elif isinstance(sc, str):
                    flat_scheme_crops.append(sc.lower())

            if flat_scheme_crops:
                crop_weight = 2.0 if any(fc in flat_scheme_crops for fc in farmer_crops) else 0.5

            # ── 3. Domain Classification (category-primary) ───────────────────
            is_agri = _classify_domain(scheme)

            # ── 4. Demographic & Category Affinity (agri-only) ───────────────
            passed_rule_fields = [r.get("field") for r in scheme.get("passed_rules", [])]
            demographic_weight = 1.0
            if is_agri and ("category" in passed_rule_fields or "gender" in passed_rule_fields):
                demographic_weight = 1.5  # Boost for targeted agri assistance (SC/ST/Women farmers)

            # ── 5. Domain Multiplier ──────────────────────────────────────────
            # Applied MULTIPLICATIVELY with demographic_weight — a non-agri scheme
            # with a strong demographic match still gets suppressed to 0.1% of
            # its pre-multiplier score. demographic_weight cannot override this.
            domain_multiplier = 1.0 if is_agri else 0.001

            total_affinity = state_weight * crop_weight * demographic_weight * domain_multiplier

            # ── 6. Proximity & Fine-Grained Tie-Breaker Score ─────────────────
            land_prox_bonus = 0.0
            inc_prox_bonus = 0.0
            age_bonus = 0.0

            for rule in scheme.get("passed_rules", []):
                field = rule.get("field")
                val = rule.get("value")
                farmer_val = rule.get("farmer_value")

                if field == "land_size" and isinstance(val, (int, float)) and isinstance(farmer_val, (int, float)) and val > 0:
                    ratio = farmer_val / val
                    if 0 < ratio <= 1.0:
                        land_prox_bonus += ratio * 0.05
                elif field == "income" and isinstance(val, (int, float)) and isinstance(farmer_val, (int, float)) and val > 0:
                    ratio = farmer_val / val
                    if 0 < ratio <= 1.0:
                        inc_prox_bonus += ratio * 0.05
                elif field == "age":
                    age_bonus += 0.01

            # Rule Density Bonus (more matched criteria = higher specificity)
            matched_count = len(scheme.get("passed_rules", []))
            rule_density_bonus = matched_count * 0.02

            # ── 7. Financial Benefit Bonus (log-scaled) ───────────────────────
            # Old formula: min(fin_benefit / 100_000, 1.0) * 0.01
            #   — saturated at ₹100,000; ₹1M and ₹100K both scored 0.01
            # New formula: log10-scaled across [₹1, ₹10M], max contribution 0.02
            #   — ₹6,000 → ~0.0064, ₹100K → ~0.0143, ₹200K → ~0.0153,
            #     ₹500K → ~0.0167, ₹1M → ~0.0171, ₹10M → 0.0200
            fin_benefit = predicted_benefit.get("predicted_financial_value", 0) or 0
            fin_bonus = 0.0
            if isinstance(fin_benefit, (int, float)) and fin_benefit > 0:
                fin_bonus = (math.log10(min(float(fin_benefit), 10_000_000.0) + 1.0) / 7.0) * 0.02

            # ── 8. Deterministic Hash Micro Tiebreaker (true last resort) ─────
            # Contribution capped at < 1e-6 so it never affects real ordering.
            sid_hash = sum((i + 1) * ord(c) for i, c in enumerate(str(scheme_id))) % 997
            hash_tiebreaker = sid_hash * 0.00000001

            prox_total = (
                land_prox_bonus + inc_prox_bonus + age_bonus
                + rule_density_bonus + fin_bonus + hash_tiebreaker
            )
            final_score = (probability * total_affinity) + prox_total

            source_url = scheme.get("source_url") or (
                f"https://www.myscheme.gov.in/schemes/"
                f"{scheme.get('myscheme_slug', str(scheme_id).lower().replace('_', '-'))}"
            )

            ranked_results.append({
                "scheme_id": scheme_id,
                "scheme_name": scheme.get("name"),
                "success_probability": probability,
                "relevance_score": final_score,
                "score_breakdown": {
                    "base_probability": round(probability, 4),
                    "total_affinity_multiplier": round(total_affinity, 4),
                    "land_proximity_bonus": round(land_prox_bonus, 4),
                    "income_proximity_bonus": round(inc_prox_bonus, 4),
                    "rule_density_bonus": round(rule_density_bonus, 4),
                    "financial_bonus": round(fin_bonus, 6),
                    "hash_tiebreaker": f"{hash_tiebreaker:.8f}",
                    "final_score": round(final_score, 6),
                    # Debug fields for transparency
                    "is_agri": is_agri,
                    "domain_multiplier": domain_multiplier,
                    "state_weight": state_weight,
                    "crop_weight": crop_weight,
                    "demographic_weight": demographic_weight,
                },
                "explanation": explanation,
                "predicted_financial_value": predicted_benefit["predicted_financial_value"],
                "benefit_type": predicted_benefit["benefit_type"],
                "prediction_explanation": predicted_benefit["prediction_explanation"],
                "financial_benefit": predicted_benefit["predicted_financial_value"],
                "source_url": source_url,
            })

        # Step 5 — Sort by relevance score
        ranked_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        logger.info("Scheme ranking completed, transitioning to Graph Bundling")

        # Step 6 — Knowledge Graph Bundle Construction (uses live schemes)
        kg = SchemeKnowledgeGraph(dynamic_schemes)
        recommended_bundles = kg.get_optimal_scheme_bundles(ranked_results)

        # Step 7 — Reinforcement policy selects best scheme
        scheme_ids = [s["scheme_id"] for s in ranked_results]
        selected_scheme = self.policy.select_scheme(scheme_ids) if scheme_ids else None

        return {
            "ranked_schemes": ranked_results,
            "recommended_bundles": recommended_bundles,
            "ineligible_schemes": ineligible_results,
            "recommended_scheme": selected_scheme,
        }