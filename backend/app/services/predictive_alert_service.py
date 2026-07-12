# backend/app/services/predictive_alert_service.py
import random
from datetime import datetime
from app.models.farmer import PredictiveAlert

class PredictiveAlertService:
    """
    Generates real-time risk alerts for a farmer based on their location,
    crop type, and historical weather heuristics.
    Ideally, this connects to an external API (like OpenWeatherMap).
    For this implementation, we use heuristic rules based on location/crop.
    """

    # Mock historical heuristics for crops by state
    CROP_RISKS = {
        "Maharashtra": {
            "Sugarcane": {"risk": "Water Scarcity", "severity": "high", "action": "Setup drip irrigation and apply for PMKSY."},
            "Cotton": {"risk": "Bollworm Pest Alert", "severity": "medium", "action": "Spray recommended pesticide and monitor crops."},
            "Onion": {"risk": "Unseasonal Rain", "severity": "critical", "action": "Harvest early if mature; ensure proper drainage."}
        },
        "Punjab": {
            "Wheat": {"risk": "High Temperature/Heat Wave", "severity": "high", "action": "Apply light irrigation during evenings."},
            "Rice": {"risk": "Groundwater Depletion", "severity": "medium", "action": "Adopt direct seeded rice (DSR) technique."}
        },
        "Default": {
            "General": {"risk": "Expected Temperature Fluctuation", "severity": "low", "action": "Monitor soil moisture regularly."}
        }
    }

    @staticmethod
    def generate_alerts(farmer_data: dict) -> list[PredictiveAlert]:
        """
        Takes a farmer profile dict and returns a list of active predictive alerts.
        """
        alerts = []
        state = farmer_data.get("state")
        crops = farmer_data.get("primary_crops") or []
        
        # If no crops listed, look at the single ML 'crop' string
        single_crop = farmer_data.get("crop")
        if single_crop and single_crop not in crops:
            crops.append(single_crop)

        # Baseline weather alert based on season
        raw_season = farmer_data.get("season")
        season = (raw_season if raw_season else "Kharif").lower()
        if season == "kharif":
            alerts.append(PredictiveAlert(
                alert_type="weather_risk",
                severity="medium",
                message="Monsoon irregularities detected in your region. Heavy rainfall expected next week.",
                timestamp=datetime.utcnow().isoformat(),
                recommended_action="Ensure drainage systems are clear in fields."
            ))
        elif season == "rabi":
            alerts.append(PredictiveAlert(
                alert_type="weather_risk",
                severity="low",
                message="Cold wave expected in the coming days.",
                timestamp=datetime.utcnow().isoformat(),
                recommended_action="Provide light irrigation to protect crops from frost."
            ))

        # Crop specific heuristic alerts
        if not state or state not in PredictiveAlertService.CROP_RISKS:
            state_risks = PredictiveAlertService.CROP_RISKS["Default"]
        else:
            state_risks = PredictiveAlertService.CROP_RISKS.get(state, PredictiveAlertService.CROP_RISKS["Default"])

        if not crops:
             alerts.append(PredictiveAlert(
                    alert_type="general_risk",
                    severity="low",
                    message="Complete your profile with crop details to receive specific pest and disease warnings.",
                    timestamp=datetime.utcnow().isoformat(),
                    recommended_action="Update crops in profile."
                ))

        for crop in crops:
            if not crop: continue
            
            # Simple fuzzy matching (capitalization)
            crop_key = crop.capitalize()
            if crop_key in state_risks:
                risk_data = state_risks[crop_key]
                alerts.append(PredictiveAlert(
                    alert_type="crop_risk",
                    severity=risk_data["severity"],
                    message=f"Alert for {crop_key}: {risk_data['risk']} detected in {state if state else 'your region'}.",
                    timestamp=datetime.utcnow().isoformat(),
                    recommended_action=risk_data["action"]
                ))
            else:
                 alerts.append(PredictiveAlert(
                    alert_type="crop_risk",
                    severity="low",
                    message=f"Monitoring conditions for {crop_key}.",
                    timestamp=datetime.utcnow().isoformat(),
                    recommended_action="Maintain regular irrigation schedules."
                ))
            
        return alerts
