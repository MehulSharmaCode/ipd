import pandas as pd
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "datasets" / "crop_recommendation_dataset.csv"
MODEL_PATH = BASE_DIR / "models" / "crop_model.pkl"


def main():

    print("Loading crop dataset...")

    df = pd.read_csv(DATA_PATH)

    print("Dataset shape:", df.shape)

    # Target column
    y = df["label"]

    # Feature columns
    X = df.drop(columns=["label"])

    # Identify categorical and numeric columns
    categorical_columns = ["soil", "season", "irrigation"]
    numeric_columns = [
        "nitrogen",
        "phosphorus",
        "potassium",
        "rainfall",
        "temperature"
    ]

    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_columns),
            ("num", "passthrough", numeric_columns),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model)
        ]
    )

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    print("Training crop recommendation model...")

    pipeline.fit(X_train, y_train)

    joblib.dump(pipeline, MODEL_PATH)

    print("✅ Crop model trained successfully")
    print("Model saved to:", MODEL_PATH)


if __name__ == "__main__":
    main()