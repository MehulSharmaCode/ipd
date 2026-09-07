from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict
from typing import List, Optional
import re


class SchemeRecommendation(BaseModel):
    scheme_id: str
    scheme_name: str
    success_probability: float
    explanation: List[str] = []
    predicted_financial_value: int = 0
    benefit_type: str = ""
    prediction_explanation: str = ""


class IneligibleScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    explanation: List[str] = []


class PredictiveAlert(BaseModel):
    alert_type: str = Field(description="e.g., 'weather_risk', 'pest_warning'")
    severity: str = Field(description="'low', 'medium', 'high', 'critical'")
    message: str = Field(description="Detailed alert message")
    timestamp: str = Field(description="When this alert was generated")
    recommended_action: Optional[str] = Field(None, description="What the farmer should do")


class SchemeBundle(BaseModel):
    bundle_id: str
    total_benefit_value: int = 0
    total_benefit: str = ""
    schemes: List[SchemeRecommendation] = []
    graph_explanation: str = ""


class FarmerProfile(BaseModel):
    # Basic Info (Required immediately)
    full_name: str = Field(..., example="Ramesh Kumar")
    email: EmailStr = Field(..., example="ramesh@example.com")
    
    # Everything below is Optional (Filled out later!)
    phone_number: Optional[str] = Field(None, example="+919876543210")
    age: Optional[int] = Field(None, ge=18)
    gender: Optional[str] = Field(None, example="Male")
    category: Optional[str] = Field(None, example="OBC")
    is_differently_abled: Optional[bool] = Field(default=False)
    highest_qualification: Optional[str] = Field(None, example="10th Pass")
    
    # Contact & Location
    state: Optional[str] = Field(None, example="Maharashtra")
    district: Optional[str] = Field(None, example="Pune")
    pincode: Optional[str] = Field(None, example="411001")
    
    # Identity & Financial
    is_verified: Optional[bool] = Field(default=False, description="Whether the farmer is verified to post stories")
    aadhar_number: Optional[str] = Field(None, example="123456789012")
    pan_number: Optional[str] = Field(None, example="ABCDE1234F")
    is_aadhar_verified: bool = Field(default=False)
    is_pan_verified: bool = Field(default=False)
    is_7_12_verified: bool = Field(default=False)
    annual_income: Optional[float] = Field(None, example=60000.0)
    bank_account_linked: Optional[bool] = Field(default=False)
    
    # 7/12 Satbara Document Fields (populated by Gemini extraction)
    owner_name: Optional[str] = Field(None, description="Land owner name from 7/12")
    survey_number: Optional[str] = Field(None, description="Survey/Bhoomapan number")
    gat_number: Optional[str] = Field(None, description="Gat number")
    village: Optional[str] = Field(None, description="Village from 7/12")
    taluka: Optional[str] = Field(None, description="Taluka from 7/12")
    land_area: Optional[str] = Field(None, description="Land area with unit")
    current_crop: Optional[str] = Field(None, description="Current crop(s)")
    land_use: Optional[str] = Field(None, description="agricultural/non-agricultural/mixed")
    co_owners: Optional[List[str]] = Field(default=None, description="Co-owner names from 7/12")
    father_name: Optional[str] = Field(None, description="Father's name from PAN")
    dob: Optional[str] = Field(None, description="Date of birth from OCR")
    birth_year: Optional[str] = Field(None, description="Birth year from OCR")
    
    # Agricultural Data
    land_size_hectares: Optional[float] = Field(None, example=1.5)
    farmer_type: Optional[str] = Field(None, example="Small")
    irrigation_type: Optional[str] = Field(None, example="Rainfed")
    soil_type: Optional[str] = Field(None, example="Alluvial")
    crop_season: Optional[str] = Field(None, example="Kharif")
    water_source: Optional[str] = Field(None, example="Well")
    land_ownership: Optional[str] = Field(None, example="Owned")
    primary_crops: List[str] = Field(default=[])
    preferred_language: str = Field(default="en", description="User's preferred UI language")
    
    # ML specific fields
    crop: Optional[str] = Field(None, example="Rice")
    temperature: Optional[float] = Field(None, example=28.5)
    rainfall: Optional[float] = Field(None, example=1200.0)
    soil: Optional[str] = Field(None, example="Loamy")
    season: Optional[str] = Field(None, example="Kharif")
    
    documents_uploaded: List[str] = Field(default=[])

    # Set to True when the user completes Step 3 of the ProfileWizard.
    # This is the PRIMARY signal used by ProtectedRoute to determine if
    # the user should be sent to /dashboard or /profile-setup.
    profile_wizard_complete: bool = Field(default=False)

    @field_validator("aadhar_number")
    @classmethod
    def validate_aadhar(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        # Remove spaces
        v = v.replace(" ", "")
        if not re.match(r"^\d{12}$", v):
            raise ValueError("Aadhaar number must be exactly 12 digits")
        return v

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        v = v.upper()
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", v):
            raise ValueError("Invalid PAN card format (e.g., ABCDE1234F)")
        return v


class FarmerUpdate(BaseModel):
    """
    Used for PUT /api/farmers/me — all fields are optional so the frontend
    doesn't need to send every field on every update.

    KEY FIX: The frontend spreads the full profile state (which has email='',
    phone_number='', etc. as empty strings). Pydantic v2 validates empty strings
    for typed fields like EmailStr and raises a 422. The model_validator below
    converts all empty strings to None BEFORE per-field validation runs.
    """
    model_config = ConfigDict(validate_default=False)

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    age: Optional[int] = Field(default=None)
    gender: Optional[str] = None
    category: Optional[str] = None
    is_differently_abled: Optional[bool] = None
    highest_qualification: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    aadhar_number: Optional[str] = None
    pan_number: Optional[str] = None
    is_aadhar_verified: Optional[bool] = None
    is_pan_verified: Optional[bool] = None
    is_7_12_verified: Optional[bool] = None
    
    # 7/12 Satbara Document Fields
    owner_name: Optional[str] = None
    survey_number: Optional[str] = None
    gat_number: Optional[str] = None
    village: Optional[str] = None
    taluka: Optional[str] = None
    land_area: Optional[str] = None
    current_crop: Optional[str] = None
    land_use: Optional[str] = None
    co_owners: Optional[List[str]] = None
    father_name: Optional[str] = None
    dob: Optional[str] = None
    birth_year: Optional[str] = None
    annual_income: Optional[float] = None
    bank_account_linked: Optional[bool] = None
    land_size_hectares: Optional[float] = None
    farmer_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    soil_type: Optional[str] = None
    crop_season: Optional[str] = None
    water_source: Optional[str] = None
    land_ownership: Optional[str] = None
    primary_crops: Optional[List[str]] = None
    preferred_language: Optional[str] = None
    crop: Optional[str] = None
    temperature: Optional[float] = None
    rainfall: Optional[float] = None
    soil: Optional[str] = None
    season: Optional[str] = None
    profile_wizard_complete: Optional[bool] = None

    @model_validator(mode='before')
    @classmethod
    def coerce_empty_strings_to_none(cls, values: dict) -> dict:
        """
        ROOT CAUSE FIX for 422 on PUT /api/farmers/me:
        The frontend spreads the entire profile state object into the PUT payload.
        This means fields like email='', phone_number='', gender='' etc. are sent
        as empty strings. Pydantic v2 does NOT automatically convert '' to None for
        typed fields like EmailStr — it tries to validate '' as an email and fails.

        This model_validator runs BEFORE any field validators, converting all empty
        string values to None so that Optional[EmailStr] etc. receive None (valid)
        instead of '' (invalid email string).
        """
        if isinstance(values, dict):
            return {
                k: (None if isinstance(v, str) and v.strip() == '' else v)
                for k, v in values.items()
            }
        return values

    @field_validator("aadhar_number")
    @classmethod
    def validate_aadhar(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.replace(" ", "").replace("-", "")
        if not re.match(r"^\d{12}$", v):
            raise ValueError("Aadhaar number must be exactly 12 digits")
        return v

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.upper().replace(" ", "")
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", v):
            raise ValueError("Invalid PAN card format (e.g., ABCDE1234F)")
        return v

    @field_validator("age", mode="before")
    @classmethod
    def validate_age(cls, v) -> Optional[int]:
        if v is None or v == "" or v == 0:
            return None
        try:
            age = int(v)
        except (TypeError, ValueError):
            return None
        if age < 1 or age > 120:
            return None
        return age



class FarmerDB(FarmerProfile):
    hashed_password: str


class FarmerResponse(FarmerProfile):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    recommended_schemes: Optional[List[SchemeRecommendation]] = []
    recommended_bundles: Optional[List[SchemeBundle]] = []
    ineligible_schemes: Optional[List[IneligibleScheme]] = []
    predictive_alerts: Optional[List[PredictiveAlert]] = []


# --- AUTH MODELS ---

class FarmerSignup(BaseModel):
    # Strictly just the essentials for creating an account
    full_name: str = Field(..., example="Ramesh Kumar")
    email: EmailStr = Field(..., example="ramesh@example.com")
    password: str = Field(..., example="SecurePassword123!")


class Token(BaseModel):
    access_token: str
    token_type: str
