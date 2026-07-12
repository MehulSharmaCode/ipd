from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime
from bson import ObjectId


class StoryBase(BaseModel):
    title: str = Field(..., description="Title of the success story")
    content: str = Field(..., description="Full text content of the story")
    crop_type: Optional[str] = Field(None, description="Crop the story relates to")
    location_state: Optional[str] = Field(None, description="State of the farmer")
    location_district: Optional[str] = Field(None, description="District of the farmer")
    scheme_id: Optional[str] = Field(None, description="ID of the scheme used (if any)")
    media_url: Optional[HttpUrl] = Field(None, description="URL to an audio or video clip")
    tags: List[str] = Field(default=[])


class StoryCreate(StoryBase):
    pass


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    crop_type: Optional[str] = None
    location_state: Optional[str] = None
    location_district: Optional[str] = None
    scheme_id: Optional[str] = None
    media_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None


class StoryDB(StoryBase):
    farmer_id: str
    farmer_name: str
    upvotes: int = Field(default=0)
    upvoted_by: List[str] = Field(default=[]) # List of farmer IDs who upvoted
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StoryResponse(StoryDB):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
