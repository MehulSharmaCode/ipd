import pandas as pd

from app.ml.models.registry import ModelRegistry
from app.ml.utils.logger import get_logger


logger = get_logger(__name__)


class SchemeSuccessPredictor:
    """
    ML inference class responsible for predicting
    scheme approval probability.
    """

    def __init__(self):

        logger.info("Loading scheme success model from registry...")

        self.model = ModelRegistry.load_model("scheme_success")

        logger.info("Scheme success model loaded successfully")

    def predict_success(self, features: dict) -> float:
        """
        Predict probability that a scheme application
        will be approved.
        """

        df = pd.DataFrame([features])

        probability = self.model.predict_proba(df)[0][1]

        return float(probability)