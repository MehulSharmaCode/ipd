def clean_farmer_profile(profile: dict) -> dict:
    """
    Normalize incoming farmer profile data for the rules engine and ML models.
    """

    cleaned = {}

    # 1. Map Income & Land Size (Handle both API and database keys)
    raw_income = profile.get("annual_income")
    if raw_income is None or raw_income == "": raw_income = profile.get("income", 0)
    try:
        cleaned["income"] = float(raw_income or 0)
    except (TypeError, ValueError):
        cleaned["income"] = 0.0

    raw_land = profile.get("land_size_hectares")
    if raw_land is None or raw_land == "": raw_land = profile.get("land_size", 0)
    try:
        cleaned["land_size"] = float(raw_land or 0)
    except (TypeError, ValueError):
        cleaned["land_size"] = 0.0

    cleaned["state"] = str(profile.get("state", "")).strip().lower()
    
    # 2. Extract Primary Crop
    # Schemes often filter by the main crop. We take the first one if multiple are provided.
    crops = profile.get("primary_crops", [])
    primary_crop = crops[0] if isinstance(crops, list) and crops else ""
    cleaned["crop"] = str(profile.get("crop") or primary_crop).strip().lower()

    # 3. Normalize Irrigation to Booleans for rules engine (YAML loads yes/no as bool)
    irr_type = str(profile.get("irrigation_type") or profile.get("irrigation", "")).strip().lower()
    if irr_type in ["rainfed", "no", "false", ""]:
        cleaned["irrigation"] = False
    else:
        cleaned["irrigation"] = True

    # 4. Derive and Normalize Farmer Type
    # This is critical as many rules filter on 'small' or 'medium' explicitly
    f_type = str(profile.get("farmer_type", "")).strip().lower()
    land = cleaned["land_size"]

    # Derive if missing
    if not f_type:
        if land <= 2: f_type = "small"
        elif land <= 5: f_type = "medium"
        else: f_type = "large"
    
    # Normalize categories to rule-engine expected terms
    if f_type in ["marginal", "small"]:
        cleaned["farmer_type"] = "small"
    elif f_type in ["semi-medium", "medium"]:
        cleaned["farmer_type"] = "medium"
    else:
        cleaned["farmer_type"] = "large"

    return cleaned