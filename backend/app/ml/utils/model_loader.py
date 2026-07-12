import joblib
from pathlib import Path


def load_model(model_path: Path):

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = joblib.load(model_path)

    return model