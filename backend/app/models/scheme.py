# backend/app/models/scheme.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime


class RuleCondition(BaseModel):
    field: str = Field(..., description="Field name in farmer profile, e.g. land_size, farmer_type")
    operator: str = Field(..., description="Comparison operator: ==, !=, <, <=, >, >=, in, not_in")
    value: Any = Field(..., description="Target value or list of values to compare against")


class BenefitCalculation(BaseModel):
    type: str = Field(default="flat_rate", description="Calculation type: flat_rate, per_hectare_subsidy, etc.")
    base_rate: Optional[float] = Field(default=None, description="Flat rate financial benefit amount")
    base_rate_per_ha: Optional[float] = Field(default=None, description="Per-hectare subsidy amount")
    crop_multiplier_enabled: Optional[bool] = Field(default=False)


class SchemeBase(BaseModel):
    scheme_id: str = Field(..., example="PM_KISAN", description="Unique scheme identifier code")
    name: str = Field(..., example="PM Kisan Samman Nidhi")
    department: Optional[str] = Field(default="Ministry of Agriculture & Farmers Welfare")
    description: Optional[str] = Field(default="Government support scheme for farmers")
    category: Optional[str] = Field(default="Financial Support", example="Financial Support")
    level: Optional[str] = Field(default="central", example="central") # 'central' or 'state'
    state: Optional[str] = Field(default=None, example="Maharashtra")
    benefit_type: Optional[str] = Field(default="Direct Benefit Transfer", example="Direct Benefit Transfer")
    benefit_calculation: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "flat_rate", "base_rate": 6000}
    )
    conflicts_with: List[str] = Field(default_factory=list, description="Scheme IDs that conflict with this scheme")
    rules: List[RuleCondition] = Field(default_factory=list, description="Eligibility rules")
    # --- myScheme.gov.in tracking fields ---
    myscheme_slug: Optional[str] = Field(default=None, description="Slug from myscheme.gov.in")
    myscheme_tags: Optional[List[str]] = Field(default=None, description="Tags from myScheme API")
    eligibility_raw: Optional[str] = Field(default=None, description="Raw eligibility text from myScheme")
    benefits_raw: Optional[str] = Field(default=None, description="Raw benefits markdown from myScheme")
    last_fetched: Optional[datetime] = Field(default=None, description="Last fetched from myScheme API")
    content_hash: Optional[str] = Field(default=None, description="SHA256 hash for change detection")

    status: str = Field(
        default="published",
        description="Status: draft, pending_review, published, archived"
    )
    source_url: Optional[str] = Field(default=None)


class SchemeCreate(SchemeBase):
    pass


class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None
    state: Optional[str] = None
    benefit_type: Optional[str] = None
    benefit_calculation: Optional[Dict[str, Any]] = None
    conflicts_with: Optional[List[str]] = None
    rules: Optional[List[RuleCondition]] = None
    status: Optional[str] = None
    source_url: Optional[str] = None
    myscheme_slug: Optional[str] = None
    myscheme_tags: Optional[List[str]] = None
    eligibility_raw: Optional[str] = None
    benefits_raw: Optional[str] = None
    last_fetched: Optional[datetime] = None
    content_hash: Optional[str] = None


class SchemeDB(SchemeBase):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SchemeResponse(SchemeBase):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None