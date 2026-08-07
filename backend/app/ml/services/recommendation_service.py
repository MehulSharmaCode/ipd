from app.ml.inference.ranking_engine import SchemeRankingEngine
from app.ml.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy singleton — loaded on first request so import failures don't crash the backend
_ranking_engine: SchemeRankingEngine | None = None


def _get_ranking_engine() -> SchemeRankingEngine | None:
    global _ranking_engine
    if _ranking_engine is None:
        try:
            _ranking_engine = SchemeRankingEngine()
        except Exception as e:
            logger.error(f"Failed to initialize SchemeRankingEngine: {e}")
    return _ranking_engine


class RecommendationService:
    """
    Service layer responsible for generating
    scheme recommendations using ML ranking engine.
    """

    @staticmethod
    def _dedupe_list(items: list) -> list:
        seen = set()
        deduped = []
        for item in items:
            sid = item.get("scheme_id") if isinstance(item, dict) else item
            if sid and sid not in seen:
                seen.add(sid)
                deduped.append(item)
        return deduped

    @staticmethod
    def get_recommendations(farmer_profile: dict, schemes: list = None):
        engine = _get_ranking_engine()

        if engine is None:
            logger.warning("SchemeRankingEngine unavailable — returning empty recommendations")
            return {"eligible": [], "bundles": [], "ineligible": []}

        try:
            results = engine.rank_schemes(farmer_profile, dynamic_schemes=schemes)
        except RuntimeError as e:
            # dynamic_schemes=None means the caller couldn't reach MongoDB.
            # Return a structured error so the API layer can surface a clear
            # "temporarily unavailable" message instead of a silent empty list.
            logger.error(f"rank_schemes DB failure: {e}")
            return {
                "eligible": [],
                "bundles": [],
                "ineligible": [],
                "error_code": "scheme_data_unavailable",
                "error_detail": (
                    "Scheme catalog could not be loaded from the database. "
                    "Recommendations are temporarily unavailable."
                ),
            }
        except Exception as e:
            logger.error(f"rank_schemes failed: {e}")
            return {"eligible": [], "bundles": [], "ineligible": []}

        eligible = RecommendationService._dedupe_list(results.get("ranked_schemes", []))
        bundles = results.get("recommended_bundles", [])
        ineligible = RecommendationService._dedupe_list(results.get("ineligible_schemes", []))

        return {
            "eligible": eligible,
            "bundles":  bundles,
            "ineligible": ineligible,
        }