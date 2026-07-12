# backend/app/api/farmers.py
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from typing import List

from app.models.farmer import FarmerProfile, FarmerResponse
from app.ml.services.recommendation_service import RecommendationService
from app.services.predictive_alert_service import PredictiveAlertService
from app.ml.inference.crop_recommender import CropRecommender
from app.core.database import get_db
from app.core.security import get_current_user
from pydantic import BaseModel

router = APIRouter(tags=["Farmers"])

# Crop Recommender instance (Mehul-Community-Feature)
_crop_recommender: CropRecommender = None

def get_crop_recommender() -> CropRecommender:
    global _crop_recommender
    if _crop_recommender is None:
        try:
            _crop_recommender = CropRecommender()
        except Exception as e:
            print(f"⚠️ Could not load CropRecommender: {e}")
    return _crop_recommender


class CropRecommendRequest(BaseModel):
    N: float = 0.0
    P: float = 0.0
    K: float = 0.0
    temperature: float = 25.0
    humidity: float = 60.0
    ph: float = 6.5
    rainfall: float = 200.0


@router.post("/recommend-crop")
async def recommend_crop(data: dict, current_user: dict = Depends(get_current_user)):
    """
    Mehul Crop Recommendation System - Fully Integrated.
    Takes farmer profile data (soil_type, crop_season, location) and deduces NPK/Weather 
    to return the best crop for the provided environmental conditions.
    """
    # 1. Map soil_type back to synthetic NPK data
    soil_mapping = {
        "Alluvial": {"N": 40, "P": 40, "K": 40, "ph": 7.0},
        "Black": {"N": 30, "P": 50, "K": 60, "ph": 7.5},
        "Red": {"N": 20, "P": 30, "K": 30, "ph": 6.0},
        "Laterite": {"N": 15, "P": 25, "K": 25, "ph": 5.5},
        "Desert": {"N": 10, "P": 20, "K": 20, "ph": 8.0},
        "Mountain": {"N": 45, "P": 40, "K": 35, "ph": 6.5},
    }
    
    # 2. Map crop_season to environmental conditions (temperature, humidity, rainfall)
    weather_mapping = {
        "Kharif": {"temperature": 30.0, "humidity": 75.0, "rainfall": 250.0},
        "Rabi": {"temperature": 20.0, "humidity": 55.0, "rainfall": 50.0},
        "Zaid": {"temperature": 35.0, "humidity": 40.0, "rainfall": 20.0},
    }

    soil_type = data.get("soil_type", "Alluvial") or "Alluvial"
    season = data.get("crop_season", "Kharif") or "Kharif"
    
    s_data = soil_mapping.get(soil_type, soil_mapping["Alluvial"])
    w_data = weather_mapping.get(season, weather_mapping["Kharif"])

    crop_features = {
        "N": float(s_data["N"]),
        "P": float(s_data["P"]),
        "K": float(s_data["K"]),
        "temperature": float(w_data["temperature"]),
        "humidity": float(w_data["humidity"]),
        "ph": float(s_data["ph"]),
        "rainfall": float(w_data["rainfall"])
    }

    recommender = get_crop_recommender()
    if recommender is None:
        raise HTTPException(status_code=503, detail="Crop recommendation model is not available.")
    
    try:
        crop = recommender.recommend_crop(crop_features)
        return {"recommended_crop": str(crop), "status": "success"}
    except Exception as e:
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
        print(f"⚠️ Recommendation Error: {str(e)}")
        farmer["recommended_schemes"] = []
        farmer["recommended_bundles"] = []
        farmer["ineligible_schemes"] = []
        
    try:
        farmer["predictive_alerts"] = PredictiveAlertService.generate_alerts(farmer)
    except Exception as e:
        print(f"⚠️ Alert Generation Error: {str(e)}")
        farmer["predictive_alerts"] = []
        
    return farmer

@router.put("/me", response_model=FarmerResponse)
async def update_my_profile(profile_data: FarmerProfile, current_user: dict = Depends(get_current_user)):
    """
    Complete or edit the profile of the currently logged-in farmer.
    """
    db = get_db()
    
    # exclude_unset=True means it will ONLY update the fields the user actually sends in the request
    update_data = profile_data.model_dump(exclude_unset=True)
    
    # Prevent updating the email or password through this route for security
    update_data.pop("email", None) 
    update_data.pop("hashed_password", None)
    
    if update_data:
        await db["farmers"].update_one(
            {"_id": ObjectId(current_user["_id"])}, 
            {"$set": update_data}
        )
    
    updated_farmer = await db["farmers"].find_one({"_id": ObjectId(current_user["_id"])})
    updated_farmer["_id"] = str(updated_farmer["_id"])
    
    try:
        recommendations = RecommendationService.get_recommendations(updated_farmer)
        print(f"📊 Profile Update: Found eligible schemes for {updated_farmer['full_name']}")
        updated_farmer["recommended_schemes"] = recommendations.get("eligible", [])
        updated_farmer["recommended_bundles"] = recommendations.get("bundles", [])
        updated_farmer["ineligible_schemes"] = recommendations.get("ineligible", [])
    except Exception as e:
        print(f"⚠️ Recommendation Error: {str(e)}")
        updated_farmer["recommended_schemes"] = []
        updated_farmer["recommended_bundles"] = []
        updated_farmer["ineligible_schemes"] = []
        
    try:
        updated_farmer["predictive_alerts"] = PredictiveAlertService.generate_alerts(updated_farmer)
    except Exception as e:
        print(f"⚠️ Alert Generation Error: {str(e)}")
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
