"""
Train Scheme Success Prediction Model

This script trains a LightGBM model to predict the probability
that a farmer's scheme application will be approved.
"""

import pandas as pd
import lightgbm as lgb
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


# ==============================
# Paths
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "datasets" / "scheme_success_dataset.csv"
MODEL_PATH = BASE_DIR / "models" / "scheme_success_model.pkl"


# ==============================
# Load Dataset
# ==============================

def load_dataset():
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"Dataset loaded: {df.shape}")
    return df


# ==============================
# Prepare Features
# ==============================

def prepare_features(df):
    print("Preparing features...")

    y = df["approved"]
    X = df.drop(columns=["approved"])

    categorical_columns = [
        "state",
        "crop",
        "irrigation",
        "farmer_type",
        "scheme"
    ]

    numeric_columns = [
        "income",
        "land_size"
    ]

    return X, y, categorical_columns, numeric_columns


# ==============================
# Build Pipeline
# ==============================

def build_pipeline(categorical_columns, numeric_columns):

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_columns),
            ("num", "passthrough", numeric_columns),
        ]
    )

    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        random_state=42
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model)
        ]
    )

    return pipeline


# ==============================
# Train Model
# ==============================

def train_model(pipeline, X_train, y_train):

    print("Training LightGBM model...")

    pipeline.fit(X_train, y_train)

    return pipeline


# ==============================
# Evaluate Model
# ==============================

def evaluate_model(pipeline, X_test, y_test):

    print("Evaluating model...")

    predictions = pipeline.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    print("\nModel Accuracy:", accuracy)

    print("\nClassification Report:")
    print(classification_report(y_test, predictions))


# ==============================
# Save Model
# ==============================

def save_model(pipeline):

    print("Saving model...")

    joblib.dump(pipeline, MODEL_PATH)

    print(f"Model saved at {MODEL_PATH}")


# ==============================
# Main Training Pipeline
# ==============================

def main():

    df = load_dataset()

    X, y, categorical_columns, numeric_columns = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    pipeline = build_pipeline(categorical_columns, numeric_columns)

    pipeline = train_model(pipeline, X_train, y_train)

    evaluate_model(pipeline, X_test, y_test)

    save_model(pipeline)


if __name__ == "__main__":
    main()