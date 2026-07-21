# backend/app/api/farmers.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from typing import List

from app.models.farmer import FarmerProfile, FarmerUpdate, FarmerResponse
from app.ml.services.recommendation_service import RecommendationService
from app.services.predictive_alert_service import PredictiveAlertService
from app.ml.inference.crop_recommender import CropRecommender
from app.core.database import get_db
from app.core.security import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Farmers"])

# Crop Recommender instance (Mehul-Community-Feature)
_crop_recommender: CropRecommender = None

def get_crop_recommender() -> CropRecommender:
    global _crop_recommender
    if _crop_recommender is None:
        try:
            _crop_recommender = CropRecommender()
        except Exception as e:
            logger.error(f"Could not load CropRecommender: {e}")
    return _crop_recommender


class CropRecommendRequest(BaseModel):
    """Request model for the recommend-crop endpoint.
    Accepts soil/season/irrigation fields which are mapped to
    the exact feature schema expected by crop_model.pkl.
    """
    soil_type: str = "Alluvial"
    crop_season: str = "Kharif"
    irrigation_type: str = "Rainfed"


@router.post("/recommend-crop")
async def recommend_crop(data: dict, current_user: dict = Depends(get_current_user)):
    """
    Mehul Crop Recommendation System - Fully Integrated.
    Takes farmer profile data (soil_type, crop_season, irrigation_type) and builds
    the exact feature vector expected by crop_model.pkl:
      nitrogen, phosphorus, potassium, rainfall, temperature, soil, season, irrigation
    """
    # 1. Map soil_type → synthetic NPK values
    soil_npk_mapping = {
        "Alluvial":  {"nitrogen": 40, "phosphorus": 40, "potassium": 40},
        "Black":     {"nitrogen": 30, "phosphorus": 50, "potassium": 60},
        "Red":       {"nitrogen": 20, "phosphorus": 30, "potassium": 30},
        "Laterite":  {"nitrogen": 15, "phosphorus": 25, "potassium": 25},
        "Desert":    {"nitrogen": 10, "phosphorus": 20, "potassium": 20},
        "Mountain":  {"nitrogen": 45, "phosphorus": 40, "potassium": 35},
    }

    # 2. Map crop_season → climate conditions
    weather_mapping = {
        "Kharif": {"temperature": 30.0, "rainfall": 250.0},
        "Rabi":   {"temperature": 20.0, "rainfall": 50.0},
        "Zaid":   {"temperature": 35.0, "rainfall": 20.0},
    }

    soil_type      = str(data.get("soil_type") or "Alluvial")
    season         = str(data.get("crop_season") or "Kharif")
    irrigation     = str(data.get("irrigation_type") or "Rainfed")

    npk     = soil_npk_mapping.get(soil_type, soil_npk_mapping["Alluvial"])
    climate = weather_mapping.get(season, weather_mapping["Kharif"])

    # Build EXACT feature dict matching crop_model.pkl column names
    crop_features = {
        "nitrogen":    float(npk["nitrogen"]),
        "phosphorus":  float(npk["phosphorus"]),
        "potassium":   float(npk["potassium"]),
        "rainfall":    float(climate["rainfall"]),
        "temperature": float(climate["temperature"]),
        "soil":        soil_type,
        "season":      season,
        "irrigation":  irrigation,
    }

    recommender = get_crop_recommender()
    if recommender is None:
        raise HTTPException(status_code=503, detail="Crop recommendation model is not available.")

    try:
        crop = recommender.recommend_crop(crop_features)
        return {"recommended_crop": str(crop), "status": "success"}
    except Exception as e:
        logger.error(f"Crop recommendation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Crop recommendation failed: {str(e)}")


@router.get("/me", response_model=FarmerResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Fetch the profile of the currently logged-in farmer.
    """
    db = get_db()
    farmer = await db["farmers"].find_one({"_id": ObjectId(current_user["_id"])})
    
    # If the user has just registered but hasn't completed the profile wizard,
    # they won't exist in the 'farmers' collection yet. Instead of failing,
    # we return a default structure.
    if not farmer:
        default_farmer = {
            "_id": current_user["_id"],
            "full_name": current_user.get("full_name", ""),
            "email": current_user.get("email", ""),
            "phone_number": current_user.get("mobile", ""),
            "recommended_schemes": [],
            "ineligible_schemes": [],
            "predictive_alerts": [],
            "profile_wizard_complete": False
        }
        try:
            default_farmer["predictive_alerts"] = PredictiveAlertService.generate_alerts(default_farmer)
        except:
            pass
        return default_farmer
    
    farmer["_id"] = str(farmer["_id"])
    
    try:
        recommendations = RecommendationService.get_recommendations(farmer)
        farmer["recommended_schemes"] = recommendations.get("eligible", [])
        farmer["recommended_bundles"] = recommendations.get("bundles", [])
        farmer["ineligible_schemes"] = recommendations.get("ineligible", [])
    except Exception as e:
        logger.warning(f"Recommendation service error: {e}")
        farmer["recommended_schemes"] = []
        farmer["recommended_bundles"] = []
        farmer["ineligible_schemes"] = []

    try:
        farmer["predictive_alerts"] = PredictiveAlertService.generate_alerts(farmer)
    except Exception as e:
        logger.warning(f"Alert generation error: {e}")
        farmer["predictive_alerts"] = []

    return farmer

@router.put("/me", response_model=FarmerResponse)
async def update_my_profile(profile_data: FarmerUpdate, current_user: dict = Depends(get_current_user)):
    """
    Complete or edit the profile of the currently logged-in farmer.
    """
    db = get_db()
    
    # exclude_unset=True: only fields explicitly sent by the client
    # exclude_none=True: don't write None values (these came from empty strings
    #   coerced to None by the model_validator — we don't want to overwrite
    #   existing DB data with null when the frontend sends email='' etc.)
    update_data = profile_data.model_dump(exclude_unset=True, exclude_none=True)
    
    # Never allow email or hashed_password to be changed via this route
    update_data.pop("email", None)
    update_data.pop("hashed_password", None)
    
    logger.info(f"Updating farmer {current_user['_id']} with fields: {list(update_data.keys())}")
    
    if update_data:
        await db["farmers"].update_one(
            {"_id": ObjectId(current_user["_id"])}, 
            {"$set": update_data}
        )
    
    updated_farmer = await db["farmers"].find_one({"_id": ObjectId(current_user["_id"])})
    if not updated_farmer:
        raise HTTPException(status_code=404, detail="Farmer profile not found.")
    updated_farmer["_id"] = str(updated_farmer["_id"])

    try:
        recommendations = RecommendationService.get_recommendations(updated_farmer)
        logger.info(f"Profile updated. Scheme recommendations refreshed.")
        updated_farmer["recommended_schemes"] = recommendations.get("eligible", [])
        updated_farmer["recommended_bundles"] = recommendations.get("bundles", [])
        updated_farmer["ineligible_schemes"] = recommendations.get("ineligible", [])
    except Exception as e:
        logger.warning(f"Recommendation service error on profile update: {e}")
        updated_farmer["recommended_schemes"] = []
        updated_farmer["recommended_bundles"] = []
        updated_farmer["ineligible_schemes"] = []

    try:
        updated_farmer["predictive_alerts"] = PredictiveAlertService.generate_alerts(updated_farmer)
    except Exception as e:
        logger.warning(f"Alert generation error on profile update: {e}")
        updated_farmer["predictive_alerts"] = []

    return updated_farmer

# =========================
# Create Farmer (Legacy/Internal)
# =========================
@router.post("/", response_model=FarmerResponse, status_code=201)
async def create_farmer(farmer: FarmerProfile):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    farmer_dict = farmer.model_dump()
    try:
        # Store farmer profile
        result = await db["farmers"].insert_one(farmer_dict)
        farmer_id = str(result.inserted_id)

        # Generate AI recommendations
        recommendations = RecommendationService.get_recommendations(farmer_dict)
        alerts = PredictiveAlertService.generate_alerts(farmer_dict)
        
        farmer_dict["_id"] = farmer_id
        farmer_dict["recommended_schemes"] = recommendations.get("eligible", [])
        farmer_dict["recommended_bundles"] = recommendations.get("bundles", [])
        farmer_dict["ineligible_schemes"] = recommendations.get("ineligible", [])
        farmer_dict["predictive_alerts"] = alerts
        return farmer_dict

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Get Farmer by ID
# =========================
@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(farmer_id: str):
    db = get_db()
    try:
        farmer = await db["farmers"].find_one({"_id": ObjectId(farmer_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid Farmer ID")

    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    farmer["_id"] = str(farmer["_id"])
    
    try:
        recommendations = RecommendationService.get_recommendations(farmer)
        farmer["recommended_schemes"] = recommendations.get("eligible", [])
        farmer["recommended_bundles"] = recommendations.get("bundles", [])
        farmer["ineligible_schemes"] = recommendations.get("ineligible", [])
    except Exception as e:
        farmer["recommended_schemes"] = []
        farmer["recommended_bundles"] = []
        farmer["ineligible_schemes"] = []

    try:
        farmer["predictive_alerts"] = PredictiveAlertService.generate_alerts(farmer)
    except Exception as e:
        farmer["predictive_alerts"] = []

    return farmer

# =========================
# Get All Farmers
# =========================
@router.get("/", response_model=List[FarmerResponse])
async def get_all_farmers():
    db = get_db()
    farmers = []
    cursor = db["farmers"].find({})
    async for farmer in cursor:
        farmer["_id"] = str(farmer["_id"])
        # We don't generate recommendations for all in the list view for performance
        farmers.append(farmer)
    return farmers
