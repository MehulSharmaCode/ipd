import pandas as pd
from pathlib import Path
from app.ml.utils.model_loader import load_model


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "crop_model.pkl"


class CropRecommender:

    def __init__(self):

        self.model = load_model(MODEL_PATH)

    def recommend_crop(self, features: dict):

        df = pd.DataFrame([features])

        crop = self.model.predict(df)[0]

        return crop 