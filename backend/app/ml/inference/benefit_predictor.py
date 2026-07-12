class BenefitPredictor:
    def __init__(self):
        # Crop multipliers for water/resource-intensive crops
        self.crop_multipliers = {
            "sugarcane": 1.5,
            "rice": 1.2,
            "cotton": 1.1,
            "wheat": 1.0
        }

    def predict_benefit(self, scheme: dict, farmer_features: dict) -> dict:
        calc_logic = scheme.get("benefit_calculation", {})
        
        # Fallback to legacy fields if the YAML wasn't fully migrated
        legacy_benefit = scheme.get("financial_benefit", 0)
        calc_type = calc_logic.get("type", "flat_rate" if legacy_benefit > 0 else "unknown")
        
        predicted_value = 0
        savings_type = "Direct Transfer"
        explanation = ""

        # Default features
        land_size = float(farmer_features.get("land_size", 1.0))
        crop = str(farmer_features.get("crop", "")).lower()

        if calc_type == "per_hectare_subsidy":
            base_rate = float(calc_logic.get("base_rate_per_ha", legacy_benefit))
            
            crop_mult = 1.0
            if calc_logic.get("crop_multiplier_enabled"):
                crop_mult = self.crop_multipliers.get(crop, 1.0)
                
            predicted_value = base_rate * land_size * crop_mult
            savings_type = "Infrastructure Savings"
            explanation = f"Calculated based on {land_size} Ha of land cultivating {crop.title() if crop else 'crops'}."
            
        elif calc_type == "flat_rate":
            predicted_value = float(calc_logic.get("base_rate", legacy_benefit))
            savings_type = "Direct Financial Transfer"
            explanation = "Flat rate direct benefit transfer."

        return {
            "predicted_financial_value": int(predicted_value),
            "benefit_type": savings_type,
            "prediction_explanation": explanation
        }
