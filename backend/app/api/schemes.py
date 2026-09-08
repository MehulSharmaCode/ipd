# backend/app/api/schemes.py
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, status
from bson import ObjectId

from app.core.database import get_db
from app.models.scheme import SchemeCreate, SchemeUpdate, SchemeResponse, SchemeDB
from app.services.crawler.timeline_extractor import evaluate_timeline_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schemes", tags=["Schemes"])


@router.get("/", response_model=List[SchemeResponse])
async def list_schemes(
    status_filter: Optional[str] = Query("published", description="Filter by status: published, pending_review, draft, all"),
    category: Optional[str] = Query(None, description="Filter by category"),
    level: Optional[str] = Query(None, description="Filter by level: central or state"),
    state: Optional[str] = Query(None, description="Filter by state name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Fetch all schemes from the database with filtering and pagination.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")

    query = {}
    if status_filter and status_filter.lower() != "all":
        query["status"] = status_filter.lower()
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if level:
        query["level"] = level.lower()
    if state:
        query["$or"] = [{"state": {"$regex": state, "$options": "i"}}, {"level": "central"}]

    cursor = db["schemes"].find(query).skip(skip).limit(limit)
    schemes = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        schemes.append(doc)

    return schemes


@router.get("/{scheme_id}", response_model=SchemeResponse)
async def get_scheme_by_id(scheme_id: str):
    """
    Get detailed scheme configuration by scheme_id code or BSON ObjectId.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")

    # Match either string code (e.g., PM_KISAN) or MongoDB ObjectId
    query = {"$or": [{"scheme_id": scheme_id}]}
    if ObjectId.is_valid(scheme_id):
        query["$or"].append({"_id": ObjectId(scheme_id)})

    scheme = await db["schemes"].find_one(query)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")

    scheme["_id"] = str(scheme["_id"])
    return scheme


_NOT_FETCHED_DOCUMENTS = {
    "status": "not_fetched", "source": None, "source_url": None,
    "fetched_at": None, "raw_markdown": None, "items": [],
    "item_count": 0, "unmatched_count": 0, "extractor_version": 1,
}
_UNKNOWN_TIMELINE = {
    "status": "unknown", "open_date": None, "close_date": None,
    "open_date_raw": None, "close_date_raw": None,
    "open_date_source": None, "close_date_source": None,
    "application_modes": [], "text_mentions": [], "fetched_at": None,
    "extractor_version": 1,
}


@router.get("/{scheme_id}/requirements")
async def get_scheme_requirements(scheme_id: str):
    """
    Full requirements record for one scheme, including the verbatim source
    markdown (stripped out of the /api/farmers/me recommendation payload to
    keep it small). Used by the Dashboard's scheme detail view and for
    auditing exactly what the app is showing farmers.

    Unauthenticated, like the rest of this router -- this is public
    government-scheme information, not personal data.

    A scheme that exists but has never been enriched returns 200 with
    required_documents.status == "not_fetched" / application_timeline.status
    == "unknown" -- "we don't know yet" is a real, honest answer, not a 404.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")

    query = {"$or": [{"scheme_id": scheme_id}]}
    if ObjectId.is_valid(scheme_id):
        query["$or"].append({"_id": ObjectId(scheme_id)})

    scheme = await db["schemes"].find_one(query)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")

    required_documents = scheme.get("required_documents") or _NOT_FETCHED_DOCUMENTS
    application_timeline = scheme.get("application_timeline") or _UNKNOWN_TIMELINE

    return {
        "status": "success",
        "scheme_id": scheme.get("scheme_id"),
        "scheme_name": scheme.get("name"),
        "source_url": scheme.get("source_url"),
        "last_fetched": scheme.get("last_fetched"),
        "required_documents": required_documents,
        "application_timeline": application_timeline,
        "timeline_state": evaluate_timeline_state(application_timeline),
    }


@router.post("/", response_model=SchemeResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_scheme(scheme_in: SchemeCreate):
    """
    Create a new scheme or update existing scheme rules.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")

    existing = await db["schemes"].find_one({"scheme_id": scheme_in.scheme_id})
    scheme_dict = scheme_in.model_dump()

    if existing:
        scheme_dict["updated_at"] = datetime.utcnow()
        await db["schemes"].update_one(
            {"scheme_id": scheme_in.scheme_id},
            {"$set": scheme_dict}
        )
        updated = await db["schemes"].find_one({"scheme_id": scheme_in.scheme_id})
        updated["_id"] = str(updated["_id"])
        return updated

    scheme_dict["created_at"] = datetime.utcnow()
    scheme_dict["updated_at"] = datetime.utcnow()
    result = await db["schemes"].insert_one(scheme_dict)
    scheme_dict["_id"] = str(result.inserted_id)
    return scheme_dict


@router.post("/{scheme_id}/approve", response_model=SchemeResponse)
async def approve_scheme(scheme_id: str):
    """
    Approve a scraped or pending scheme to make it live for farmer eligibility rules.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")

    query = {"$or": [{"scheme_id": scheme_id}]}
    if ObjectId.is_valid(scheme_id):
        query["$or"].append({"_id": ObjectId(scheme_id)})

    scheme = await db["schemes"].find_one(query)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")

    await db["schemes"].update_one(
        {"_id": scheme["_id"]},
        {"$set": {"status": "published", "updated_at": datetime.utcnow()}}
    )

    approved = await db["schemes"].find_one({"_id": scheme["_id"]})
    approved["_id"] = str(approved["_id"])
    logger.info(f"Scheme {scheme_id} approved and published.")
    return approved


@router.get("/monitoring/logs")
async def get_ingestion_logs(limit: int = 20):
    """
    Fetch government scheme crawler & ingestion activity logs.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")

    cursor = db["scheme_ingestion_log"].find().sort("scraped_at", -1).limit(limit)
    logs = []
    async for log in cursor:
        log["_id"] = str(log["_id"])
        logs.append(log)

    return {"status": "success", "count": len(logs), "logs": logs}
