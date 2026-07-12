# backend/app/models/scheme.py
from pydantic import BaseModel, Field
from typing import List, Optional

class EligibilityCriteria(BaseModel):
    min_age: Optional[int] = 18
    max_land_size_hectares: Optional[float] = None
    allowed_states: Optional[List[str]] = None
    target_farmer_types: Optional[List[str]] = None

class Scheme(BaseModel):
    scheme_name: str = Field(..., example="PM-KISAN")
    department: str = Field(..., example="Ministry of Agriculture")
    description: str = Field(..., example="Income support scheme for landholding farmers.")
    financial_benefit_amount: float = Field(..., example=6000.0)
    
    # This is what our Rule Engine will check against
    eligibility: EligibilityCriteria

class SchemeResponse(Scheme):
    id: str = Field(..., alias="_id")