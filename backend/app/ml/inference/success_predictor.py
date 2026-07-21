import pandas as pd

from app.ml.models.registry import ModelRegistry
from app.ml.utils.logger import get_logger


logger = get_logger(__name__)

# Exact feature column order expected by the trained scheme_success_model.pkl Pipeline
FEATURE_COLUMNS = ["income", "land_size", "state", "crop", "irrigation", "farmer_type", "scheme"]


class SchemeSuccessPredictor:
    """
    ML inference class responsible for predicting scheme approval probability.

    The underlying scheme_success_model.pkl (LGBMClassifier Pipeline) was trained on:
        income, land_size, state, crop, irrigation, farmer_type, scheme
    """

    def __init__(self):
        logger.info("Loading scheme success model from registry...")
        self.model = ModelRegistry.load_model("scheme_success")
        logger.info("Scheme success model loaded successfully")

    def predict_success(self, features: dict) -> float:
        """
        Predict probability that a scheme application will be approved.

        Args:
            features: dict with keys matching FEATURE_COLUMNS.
        Returns:
            float probability in [0, 1]
        """
        # Ensure columns are in exact training order to suppress LightGBM feature name warnings
        ordered_features = {col: features.get(col, "") for col in FEATURE_COLUMNS}
        df = pd.DataFrame([ordered_features], columns=FEATURE_COLUMNS)

        probability = self.model.predict_proba(df)[0][1]
        return float(probability)