"""
Profile Mapper — converts FastAPI farmer schema into ML model features.

The scheme success model expects:
  income, land_size, state, crop, irrigation, farmer_type, scheme

The crop recommendation model (crop_model.pkl) was trained on:
  N, P, K, temperature, humidity, ph, rainfall
"""
from app.ml.inference.crop_recommender import CropRecommender
from app.ml.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy singleton — loaded once on first use so import failures don't crash startup
_crop_model: CropRecommender | None = None


def _get_crop_model() -> CropRecommender | None:
    global _crop_model
    if _crop_model is None:
        try:
            _crop_model = CropRecommender()
        except Exception as e:
            logger.warning(f"CropRecommender could not be loaded: {e}")
    return _crop_model


def map_farmer_to_ml_features(api_profile: dict) -> dict:
    """
    Convert (already-cleaned) farmer profile into ML model input features.
    """
    income = api_profile.get("annual_income") or api_profile.get("income") or 0
    land_size = api_profile.get("land_size_hectares") or api_profile.get("land_size") or 0
    irrigation = api_profile.get("irrigation_type") or api_profile.get("irrigation") or ""

    # Use crop if provided directly
    crop = api_profile.get("crop") or ""

    # If crop is missing → use ML crop recommender
    if not crop:
        try:
            model = _get_crop_model()
            if model:
                # crop_model.pkl is trained on: N, P, K, temperature, humidity, ph, rainfall
                crop_features = {
                    "N":           float(api_profile.get("N") or api_profile.get("nitrogen", 50)),
                    "P":           float(api_profile.get("P") or api_profile.get("phosphorus", 50)),
                    "K":           float(api_profile.get("K") or api_profile.get("potassium", 50)),
                    "temperature": float(api_profile.get("temperature", 25)),
                    "humidity":    float(api_profile.get("humidity", 60)),
                    "ph":          float(api_profile.get("ph", 6.5)),
                    "rainfall":    float(api_profile.get("rainfall", 200)),
                }
                crop = str(model.recommend_crop(crop_features)).lower()
        except Exception as e:
            logger.warning(f"Crop recommendation failed, defaulting to empty: {e}")
            crop = ""

    mapped_profile = {
        "income":       income,
        "land_size":    land_size,
        "state":        str(api_profile.get("state", "")).lower(),
        "crop":         str(crop).lower(),
        "irrigation":   str(irrigation).lower(),
        "farmer_type":  str(api_profile.get("farmer_type", "")).lower(),
        "scheme":       "pm_kisan",   # placeholder — overwritten per-scheme during ranking
    }

    return mapped_profile