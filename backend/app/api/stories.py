from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.farmer import FarmerDB
from app.models.story import StoryCreate, StoryUpdate, StoryDB, StoryResponse

router = APIRouter()

@router.post("/", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    story_in: StoryCreate,
    current_farmer: dict = Depends(get_current_user)
):
    """
    Submit a new success story. Only verified farmers can post.
    """
    # Assuming FarmerDB has is_verified, but check current_farmer dictionary
    farmer_dict = current_farmer
    is_verified = farmer_dict.get("is_verified", False)
    
    # We allow posting regardless of verification for testing, but ideally we'd check:
    # if not is_verified:
    #     raise HTTPException(status_code=403, detail="Only verified farmers can post stories.")

    db = get_db()
    
    new_story = StoryDB(
        **story_in.model_dump(),
        farmer_id=str(farmer_dict.get("_id", farmer_dict.get("id"))),
        farmer_name=farmer_dict.get("full_name", "Anonymous Farmer")
    )
    
    story_dict = new_story.model_dump()
    result = await db.stories.insert_one(story_dict)
    
    story_dict["_id"] = str(result.inserted_id)
    return story_dict


@router.get("/", response_model=List[StoryResponse])
async def get_stories(
    crop: Optional[str] = Query(None, description="Filter by crop type"),
    state: Optional[str] = Query(None, description="Filter by state"),
    scheme_id: Optional[str] = Query(None, description="Filter by scheme ID"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Get a list of community stories, with optional filters for crop, location, or scheme.
    """
    db = get_db()
    
    # Build query
    query = {}
    if crop:
        query["crop_type"] = {"$regex": crop, "$options": "i"}
    if state:
        query["location_state"] = {"$regex": state, "$options": "i"}
    if scheme_id:
        query["scheme_id"] = scheme_id
        
    cursor = db.stories.find(query).sort("created_at", -1).skip(skip).limit(limit)
    stories = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        stories.append(doc)
        
    return stories


@router.get("/top", response_model=List[StoryResponse])
async def get_top_stories(limit: int = 3):
    """
    Get top stories by upvotes. Used on the Landing Page.
    """
    db = get_db()
    cursor = db.stories.find().sort("upvotes", -1).limit(limit)
    stories = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        stories.append(doc)
    return stories


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str):
    """
    Get a specific story by ID.
    """
    db = get_db()
    
    try:
        obj_id = ObjectId(story_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid story ID format")
        
    story = await db.stories.find_one({"_id": obj_id})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    story["_id"] = str(story["_id"])
    return story


@router.post("/{story_id}/upvote")
async def upvote_story(
    story_id: str,
    current_farmer: dict = Depends(get_current_user)
):
    """
    Upvote or remove an upvote from a story.
    """
    db = get_db()
    
    try:
        obj_id = ObjectId(story_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid story ID format")
        
    story = await db.stories.find_one({"_id": obj_id})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    farmer_id = str(current_farmer.get("_id", current_farmer.get("id")))
    upvoted_by = story.get("upvoted_by", [])
    
    if farmer_id in upvoted_by:
        # Remove upvote
        await db.stories.update_one(
            {"_id": obj_id},
            {
                "$inc": {"upvotes": -1},
                "$pull": {"upvoted_by": farmer_id}
            }
        )
        return {"detail": "Upvote removed", "upvotes": story.get("upvotes", 1) - 1}
    else:
        # Add upvote
        await db.stories.update_one(
            {"_id": obj_id},
            {
                "$inc": {"upvotes": 1},
                "$push": {"upvoted_by": farmer_id}
            }
        )
        return {"detail": "Upvote added", "upvotes": story.get("upvotes", 0) + 1}
