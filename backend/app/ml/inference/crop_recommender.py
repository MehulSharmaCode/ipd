"""
Crop Recommender
-----------------
Wraps the crop_model.pkl (RandomForestClassifier Pipeline) to predict the
best crop for a given soil/weather profile.

The model was trained on these EXACT column names:
    nitrogen, phosphorus, potassium, rainfall, temperature, soil, season, irrigation

IMPORTANT: Legacy code used {N, P, K, humidity, ph} which caused:
    ValueError: columns are missing: {'nitrogen', 'phosphorus', ...}

This module accepts both old aliases (N/P/K) and the correct names.
"""

import pandas as pd
from pathlib import Path
from app.ml.utils.model_loader import load_model


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "crop_model.pkl"

# Exact feature column order expected by the trained Pipeline
FEATURE_COLUMNS = [
    "nitrogen",
    "phosphorus",
    "potassium",
    "rainfall",
    "temperature",
    "soil",
    "season",
    "irrigation",
]


class CropRecommender:
    """
    Crop recommendation model.

    Expected input keys (use recommend_crop with these or legacy aliases):
        nitrogen    (or N)
        phosphorus  (or P)
        potassium   (or K)
        rainfall
        temperature
        soil        (or soil_type)  — e.g. "Alluvial", "Black", "Red"
        season      (or crop_season) — e.g. "Kharif", "Rabi", "Zaid"
        irrigation  (or irrigation_type) — e.g. "Rainfed", "Canal", "Drip"
    """

    def __init__(self):
        self.model = load_model(MODEL_PATH)

    def recommend_crop(self, features: dict) -> str:
        """
        Predict the best crop.

        Accepts both full names and legacy short aliases.
        Returns the predicted crop name as a string.
        """
        # Resolve aliases so both old and new callers work
        resolved = {
            "nitrogen":    float(features.get("nitrogen") or features.get("N") or 50),
            "phosphorus":  float(features.get("phosphorus") or features.get("P") or 50),
            "potassium":   float(features.get("potassium") or features.get("K") or 50),
            "rainfall":    float(features.get("rainfall") or 200),
            "temperature": float(features.get("temperature") or 25),
            "soil":        str(features.get("soil") or features.get("soil_type") or "Alluvial"),
            "season":      str(features.get("season") or features.get("crop_season") or "Kharif"),
            "irrigation":  str(features.get("irrigation") or features.get("irrigation_type") or "Rainfed"),
        }

        df = pd.DataFrame([resolved], columns=FEATURE_COLUMNS)
        crop = self.model.predict(df)[0]
        return str(crop)