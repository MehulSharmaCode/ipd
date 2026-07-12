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
    def get_recommendations(farmer_profile: dict):
        engine = _get_ranking_engine()

        if engine is None:
            logger.warning("SchemeRankingEngine unavailable — returning empty recommendations")
            return {"eligible": [], "bundles": [], "ineligible": []}

        try:
            results = engine.rank_schemes(farmer_profile)
        except Exception as e:
            logger.error(f"rank_schemes failed: {e}")
            return {"eligible": [], "bundles": [], "ineligible": []}

        return {
            "eligible": results.get("ranked_schemes", []),
            "bundles":  results.get("recommended_bundles", []),
            "ineligible": results.get("ineligible_schemes", []),
        }