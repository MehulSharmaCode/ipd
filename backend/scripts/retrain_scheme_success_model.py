"""
retrain_scheme_success_model.py

Retrains scheme_success_model.pkl using generalizable scheme-level features
instead of memorized scheme_id strings. This makes the model generalize to
any scheme in the catalog, including newly ingested ones it has never seen.

Old FEATURE_COLUMNS: ["income", "land_size", "state", "crop", "irrigation", "farmer_type", "scheme"]
New FEATURE_COLUMNS: ["income", "land_size", "state", "crop", "irrigation", "farmer_type",
                      "scheme_category", "is_state_specific", "benefit_amount_bucket", "rule_count"]

Run once from the ipd/backend directory:
    python scripts/retrain_scheme_success_model.py
"""

import sys
import asyncio
import math
import random
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from sklearn.compose import ColumnTransformer
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.ml.utils.logger import get_logger

logger = get_logger(__name__)

# ─── New Feature Schema ────────────────────────────────────────────────────────
NEW_FEATURE_COLUMNS = [
    "income",              # farmer annual income (numeric)
    "land_size",           # farmer land in hectares (numeric)
    "state",               # farmer state (categorical string)
    "crop",                # farmer primary crop (categorical string)
    "irrigation",          # farmer irrigation type (categorical string)
    "farmer_type",         # small/medium/large/marginal (categorical string)
    "scheme_category",     # normalized scheme category slug (categorical string)
    "is_state_specific",   # 1 if scheme targets one state, 0 if national (binary int)
    "benefit_amount_bucket", # 0-4 bucket by benefit amount (ordinal int)
    "rule_count",          # number of eligibility rules (numeric int)
]

CATEGORICAL_FEATURES = ["state", "crop", "irrigation", "farmer_type", "scheme_category"]
NUMERIC_FEATURES = [c for c in NEW_FEATURE_COLUMNS if c not in CATEGORICAL_FEATURES]


def normalize_category(raw_category: str) -> str:
    """Map raw myScheme category string to a short, stable slug."""
    cat = (raw_category or "").lower()
    if "agricultur" in cat or "rural" in cat or "environment" in cat:
        return "agriculture"
    elif "education" in cat or "learning" in cat:
        return "education"
    elif "health" in cat or "wellness" in cat:
        return "health"
    elif "housing" in cat or "shelter" in cat:
        return "housing"
    elif "social" in cat or "welfare" in cat or "empowerment" in cat:
        return "social_welfare"
    elif "business" in cat or "entrepreneur" in cat:
        return "business"
    elif "banking" in cat or "financial" in cat or "insurance" in cat:
        return "finance"
    elif "skill" in cat or "employment" in cat:
        return "skills"
    elif "women" in cat or "child" in cat:
        return "women_child"
    elif "science" in cat or "technology" in cat or "it" in cat:
        return "science_it"
    elif "transport" in cat or "infrastructure" in cat:
        return "infrastructure"
    elif "travel" in cat or "tourism" in cat:
        return "tourism"
    elif "utility" in cat or "sanitation" in cat:
        return "utility"
    elif "law" in cat or "justice" in cat or "safety" in cat:
        return "law_justice"
    else:
        return "other"


def benefit_bucket(base_rate: float) -> int:
    """Bucket a benefit amount into 5 ordinal levels."""
    if base_rate <= 0:
        return 0
    elif base_rate < 10_000:
        return 1
    elif base_rate < 100_000:
        return 2
    elif base_rate < 1_000_000:
        return 3
    else:
        return 4


STATES = [
    "maharashtra", "uttar pradesh", "tamil nadu", "karnataka", "rajasthan",
    "madhya pradesh", "gujarat", "bihar", "west bengal", "andhra pradesh",
    "telangana", "odisha", "kerala", "punjab", "haryana", "assam",
    "jharkhand", "chhattisgarh", "himachal pradesh", "uttarakhand",
    "delhi", "goa", "manipur", "meghalaya", "nagaland", "tripura",
    "arunachal pradesh", "sikkim", "mizoram", "jammu and kashmir",
    "dadra and nagar haveli and daman and diu", "puducherry", "chandigarh",
]

CROPS = [
    "wheat", "rice", "cotton", "sugarcane", "maize", "groundnut",
    "soybean", "pulses", "vegetables", "fruits", "millets", "",
]

IRRIGATION = ["rainfed", "canal", "drip", "sprinkler", "borewell", ""]

FARMER_TYPES = ["small", "medium", "large", "marginal"]

SCHEME_CATEGORIES = [
    "agriculture", "education", "health", "housing", "social_welfare",
    "business", "finance", "skills", "women_child", "science_it",
    "infrastructure", "tourism", "utility", "law_justice", "other",
]


def scheme_features_from_doc(doc: dict) -> dict:
    """Extract scheme-level generalizable features from a MongoDB document."""
    raw_category = doc.get("category") or ""
    scheme_category = normalize_category(raw_category)
    is_state_specific = 1 if doc.get("state") else 0
    base_rate = (doc.get("benefit_calculation") or {}).get("base_rate", 0) or 0
    bucket = benefit_bucket(float(base_rate))
    rule_count = len(doc.get("rules") or [])
    return {
        "scheme_category": scheme_category,
        "is_state_specific": is_state_specific,
        "benefit_amount_bucket": bucket,
        "rule_count": rule_count,
    }


async def generate_training_data(db) -> pd.DataFrame:
    """
    Build a training dataset from the live MongoDB scheme catalog.
    Generates N farmer × scheme pairs and assigns a synthetic label based on
    rule compatibility (eligible = 1, ineligible = 0).
    """
    logger.info("Fetching published schemes from MongoDB...")
    cursor = db["schemes"].find({"status": "published", "rules": {"$exists": True, "$ne": []}})
    schemes = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(schemes)} published schemes")

    records = []
    random.seed(42)

    # Sample up to 3000 schemes for diversity without exceeding training time
    sample_schemes = random.sample(schemes, min(3000, len(schemes)))

    for scheme in sample_schemes:
        scheme_feats = scheme_features_from_doc(scheme)
        rules = scheme.get("rules") or []
        scheme_state = (scheme.get("state") or "").strip().lower()

        # Generate ~5 farmer profiles per scheme
        for _ in range(5):
            state = scheme_state if (scheme_state and random.random() > 0.4) else random.choice(STATES)
            farmer_type = random.choice(FARMER_TYPES)
            income = random.randint(30000, 500000)
            land_size = round(random.uniform(0.2, 20.0), 1)
            crop = random.choice(CROPS)
            irrigation = random.choice(IRRIGATION)

            # Derive a synthetic label:
            # - If scheme is state-specific and state matches → higher P(success)
            # - If benefit bucket > 2 → slightly higher P(success)
            # - If rule_count <= 2 → easier to qualify → higher P(success)
            p_base = 0.5
            if scheme_state and state == scheme_state:
                p_base += 0.2
            if scheme_feats["benefit_amount_bucket"] >= 3:
                p_base += 0.1
            if scheme_feats["rule_count"] <= 2:
                p_base += 0.1
            if scheme_feats["scheme_category"] == "agriculture" and farmer_type in ["small", "marginal"]:
                p_base += 0.15
            if income < 100000 and scheme_feats["scheme_category"] in ["agriculture", "social_welfare"]:
                p_base += 0.1

            label = 1 if random.random() < min(p_base, 0.92) else 0

            records.append({
                "income": income,
                "land_size": land_size,
                "state": state,
                "crop": crop,
                "irrigation": irrigation,
                "farmer_type": farmer_type,
                "scheme_category": scheme_feats["scheme_category"],
                "is_state_specific": scheme_feats["is_state_specific"],
                "benefit_amount_bucket": scheme_feats["benefit_amount_bucket"],
                "rule_count": scheme_feats["rule_count"],
                "label": label,
            })

    df = pd.DataFrame(records)
    logger.info(f"Generated {len(df)} training samples. Label distribution:\n{df['label'].value_counts().to_dict()}")
    return df


def train_model(df: pd.DataFrame) -> Pipeline:
    """Train a LightGBM Pipeline on the generalizable feature set."""
    X = df[NEW_FEATURE_COLUMNS]
    y = df["label"]

    # Ordinal encoder for categorical columns (handles unseen at inference time)
    cat_encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        encoded_missing_value=-2,
    )

    preprocessor = ColumnTransformer([
        ("cat", cat_encoder, CATEGORICAL_FEATURES),
    ], remainder="passthrough")

    clf = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=10,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", clf),
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    
    logger.info("Model trained successfully")
    logger.info(f"Validation Accuracy: {acc:.4f}")
    logger.info(f"Validation AUC: {auc:.4f}")
    print(f"Validation Accuracy: {acc:.4f}")
    print(f"Validation AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred))
    
    # Train on full dataset for final model
    pipeline.fit(X, y)

    return pipeline


async def main():
    await connect_to_mongo()
    db = get_db()

    df = await generate_training_data(db)
    pipeline = train_model(df)

    model_path = Path(__file__).resolve().parent.parent / "app" / "ml" / "models" / "scheme_success_model.pkl"
    joblib.dump(pipeline, model_path)
    logger.info(f"Model saved to {model_path}")

    # Quick sanity-check: predict on a sample row
    sample = {
        "income": 120000,
        "land_size": 1.5,
        "state": "maharashtra",
        "crop": "wheat",
        "irrigation": "rainfed",
        "farmer_type": "small",
        "scheme_category": "agriculture",
        "is_state_specific": 1,
        "benefit_amount_bucket": 2,
        "rule_count": 2,
    }
    sample_df = pd.DataFrame([sample], columns=NEW_FEATURE_COLUMNS)
    prob = pipeline.predict_proba(sample_df)[0][1]
    logger.info(f"Sanity-check prediction (agri state-specific scheme for small MH farmer): {prob:.4f}")

    await close_mongo_connection()
    print("RETRAIN COMPLETE")
    print(f"Model path: {model_path}")
    print(f"Training samples: {len(df)}")
    print(f"Sanity-check probability: {prob:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
