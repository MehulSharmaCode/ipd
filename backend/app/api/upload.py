# backend/app/api/upload.py
"""
Document Upload Endpoint
------------------------
Responsibility: Accept a file upload, save it, route it through the
Intelligent Document Processing Engine, update the farmer's database
record, and return structured extraction results.

Business logic lives in app.document_processing — NOT here.
The DocumentRouter dispatches to the correct processor (OCR or Gemini)
based on the doc_type parameter.
"""

import os
import uuid
import logging
from bson import ObjectId
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from app.core.security import get_current_user
from app.core.database import get_db

# Import the document processing engine (triggers processor registration)
import app.document_processing.ocr     # noqa: F401 — registers aadhar/pan processors
import app.document_processing.vision  # noqa: F401 — registers 7_12 processor
from app.document_processing.router import document_router

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory — relative to the working directory (backend/)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# File size limit: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Allowed MIME types
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/webp",
}


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(
        ...,
        description="Type of document. Accepted values: 'aadhar', 'pan', '7_12'",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a document for intelligent extraction.

    Supported document types:
      - 'aadhar' / 'aadhaar' — Aadhaar card (Tesseract OCR)
      - 'pan' — PAN card (Tesseract OCR)
      - '7_12' — Maharashtra 7/12 Satbara extract (Gemini Vision)

    The DocumentRouter dispatches to the correct processor.
    All processors return the same standardised ExtractionResult schema.
    """
    db = get_db()

    # ── Validation: file type ─────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type '{file.content_type}'. "
                f"Accepted types: PDF, JPEG, PNG, WebP."
            ),
        )

    # ── Validation: file size (read once, check, then save) ──────────
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the 10 MB limit.",
        )

    # ── Generate a secure unique filename ────────────────────────────
    file_ext = os.path.splitext(file.filename or "upload")[1].lower() or ".bin"
    safe_doc_type = doc_type.lower().replace("/", "_").replace("..", "")
    unique_filename = (
        f"{current_user['_id']}_{safe_doc_type}_{uuid.uuid4().hex[:8]}{file_ext}"
    )
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # ── Save file to disk ─────────────────────────────────────────────
    try:
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Saved upload: '{unique_filename}' ({len(file_bytes)} bytes)")
    except OSError as e:
        logger.error(f"Failed to save file '{unique_filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # ── Route through Document Processing Engine ─────────────────────
    extraction_result = document_router.route(file_path, doc_type=safe_doc_type)

    # ── Document type mismatch rejection ─────────────────────────────
    if not extraction_result.success and extraction_result.error:
        # Check if this is a document type mismatch (processor returns
        # success=False with a descriptive error when the classified type
        # doesn't match the expected type).
        raise HTTPException(
            status_code=400,
            detail=extraction_result.error,
        )

    # ── Semantic Normalization ────────────────────────────────────────
    from app.document_processing.normalizer import SemanticNormalizer
    normalizer = SemanticNormalizer()
    extraction_result = normalizer.normalize(extraction_result)

    # ── Business Rules Validation ─────────────────────────────────────
    extraction_result = normalizer.validate_business_rules(extraction_result)

    result_dict = extraction_result.to_dict()

    logger.info(
        f"Extraction result: type={extraction_result.document_type}, "
        f"success={extraction_result.success}, "
        f"fields={extraction_result.populated_field_names}, "
        f"time={extraction_result.processing_time_ms:.0f}ms"
    )

    # ── Build profile update via ProfileBuilder ────────────────────────
    from app.document_processing.profile_builder import FarmerProfileBuilder
    from app.document_processing.validator import DocumentValidator

    builder = FarmerProfileBuilder()
    set_fields = builder.build_update(extraction_result)

    # ── Cross-document validation ─────────────────────────────────────
    validator = DocumentValidator()
    existing_farmer = await db["farmers"].find_one(
        {"_id": ObjectId(current_user["_id"])}
    )
    validation_summary = validator.validate(set_fields, existing_farmer, safe_doc_type)

    # ── Persist document reference & extracted fields to DB ───────────
    document_record = f"{safe_doc_type}:{file_path}"
    db_update: dict = {
        "$addToSet": {"documents_uploaded": document_record}
    }
    if set_fields:
        db_update["$set"] = set_fields

    try:
        await db["farmers"].update_one(
            {"_id": ObjectId(current_user["_id"])},
            db_update,
        )
    except Exception as e:
        # DB update failure is non-fatal — we still return extraction results
        logger.error(f"DB update failed for user {current_user['_id']}: {e}")

    response = {
        "status": "success",
        "filename": unique_filename,
        "documentType": extraction_result.document_type,
        "fields": result_dict["fields"],
        "validation": result_dict["validation"],
        "processingTimeMs": result_dict["processing_time_ms"],
    }

    if validation_summary.has_conflicts:
        response["cross_document_validation"] = validation_summary.to_dict()

    if extraction_result.error:
        response["error"] = extraction_result.error

    return response