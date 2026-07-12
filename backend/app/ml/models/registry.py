from pathlib import Path
import joblib


class ModelRegistry:
    """
    Centralized model registry used to load ML models.
    """

    BASE_DIR = Path(__file__).resolve().parent
    MODEL_DIR = BASE_DIR

    MODELS = {
        "scheme_success": "scheme_success_model.pkl",
        "crop_model": "crop_model.pkl"
    }

    @classmethod
    def load_model(cls, model_name: str):

        model_file = cls.MODELS.get(model_name)

        if not model_file:
            raise ValueError(f"Model '{model_name}' not registered")

        model_path = cls.MODEL_DIR / model_file

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        return joblib.load(model_path)