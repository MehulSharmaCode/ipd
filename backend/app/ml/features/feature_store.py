from app.ml.preprocessing.data_cleaning import clean_farmer_profile
from app.ml.preprocessing.feature_engineering import add_derived_features


class FeatureStore:
    """
    Centralized feature builder used by
    training, inference, and ranking engines.
    """

    def build_features(self, profile: dict) -> dict:
        """
        Build normalized ML features from farmer profile.
        """

        # Step 1 — Clean raw API input
        profile = clean_farmer_profile(profile)

        # Step 2 — Feature engineering
        profile = add_derived_features(profile)

        return profile