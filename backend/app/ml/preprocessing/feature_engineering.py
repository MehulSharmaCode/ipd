def add_derived_features(features: dict) -> dict:
    """
    Add derived features used by ML models
    """

    income = features["income"]
    land = features["land_size"]

    # derived feature
    income_per_acre = income / max(land, 0.1)

    # store but not used by model
    features["income_per_acre"] = income_per_acre

    return features