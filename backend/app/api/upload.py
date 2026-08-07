# backend/app/api/upload.py
"""
Document Upload Endpoint
------------------------
Responsibility: Accept a file upload, save it, run the OCR pipeline,
update the farmer's database record, and return structured OCR results.

Business logic lives in app.ml.ocr.pipeline — NOT here.
"""

import os
import uuid
import logging
from bson import ObjectId
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from app.core.security import get_current_user
from app.core.database import get_db
from app.ml.ocr.pipeline import process as run_ocr_pipeline

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
        description="Type of document. Accepted values: 'aadhar', 'pan'",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a government ID document (Aadhaar or PAN) for OCR verification.

    The OCR pipeline will:
      1. Preprocess the image (denoise, deskew, threshold)
      2. Extract text using Tesseract (/opt/homebrew/bin/tesseract)
      3. Classify the document type
      4. Parse structured fields (name, DOB, ID number, gender)
      5. Validate the extracted fields
      6. Map fields to farmer profile suggestions

    Returns structured JSON with extracted fields and auto-fill suggestions.
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

    # ── Run OCR Pipeline ─────────────────────────────────────────────
    ocr_result = run_ocr_pipeline(file_path, expected_doc_type=doc_type)
    result_dict = ocr_result.to_dict()

    logger.info(
        f"OCR pipeline result: type={ocr_result.documentType}, "
        f"valid={ocr_result.validation.get('valid')}, "
        f"time={ocr_result.processingTimeMs:.0f}ms"
    )

    # ── Persist document reference & verified fields to DB ───────────
    document_record = f"{safe_doc_type}:{file_path}"
    db_update: dict = {
        "$addToSet": {"documents_uploaded": document_record}
    }
    set_fields: dict = {}

    # Only persist verified ID numbers / land details when validation passed
    if ocr_result.validation.get("valid"):
        extracted = ocr_result.fields
        suggestions = ocr_result.profileSuggestions

        if safe_doc_type in {"aadhar", "aadhaar"} and extracted.get("aadhaarNumber"):
            clean_aadhar = extracted["aadhaarNumber"].replace(" ", "")
            set_fields["aadhar_number"] = clean_aadhar
            set_fields["aadhar_last4"] = clean_aadhar[-4:]
            set_fields["is_aadhar_verified"] = True

        elif safe_doc_type == "pan" and extracted.get("panNumber"):
            set_fields["pan_number"] = extracted["panNumber"].upper()
            set_fields["is_pan_verified"] = True

        elif safe_doc_type in {"satbara", "satbara_7_12", "7_12", "7/12"}:
            if suggestions.get("land_size_hectares"):
                set_fields["land_size_hectares"] = suggestions["land_size_hectares"]
            if suggestions.get("village"):
                set_fields["village"] = suggestions["village"]
            if suggestions.get("taluka"):
                set_fields["taluka"] = suggestions["taluka"]
            if suggestions.get("district"):
                set_fields["district"] = suggestions["district"]
            if suggestions.get("state"):
                set_fields["state"] = suggestions["state"]
            set_fields["is_land_record_verified"] = True

    if set_fields:
        db_update["$set"] = set_fields

    try:
        await db["farmers"].update_one(
            {"_id": ObjectId(current_user["_id"])},
            db_update,
        )
    except Exception as e:
        # DB update failure is non-fatal — we still return OCR results
        logger.error(f"DB update failed for user {current_user['_id']}: {e}")

    # ── Build response ────────────────────────────────────────────────
    # Always return success=True if the file was saved (OCR is best-effort)
    return {
        "status": "success",
        "filename": unique_filename,
        "documentType": result_dict["documentType"],
        "confidence": result_dict["confidence"],
        "fields": result_dict["fields"],
        "validation": result_dict["validation"],
        "profileSuggestions": result_dict["profileSuggestions"],
        "processingTimeMs": result_dict["processingTimeMs"],
        # rawTextSnippet only in debug — do not expose in production
        # "rawTextSnippet": result_dict["rawTextSnippet"],
    }