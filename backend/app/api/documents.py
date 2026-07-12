"""
Documents Router
-----------------
Legacy /documents/verify endpoint — redirects to the new modular OCR pipeline.
The old DocumentPipeline has been superseded by app.ml.ocr.pipeline.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os

from app.ml.ocr.pipeline import process as run_ocr_pipeline

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/verify")
async def verify_document(file: UploadFile = File(...)):
    """
    Verify a document using the OCR pipeline.
    Supersedes the old DocumentPipeline-based endpoint.
    """
    file_path = f"temp_{file.filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = run_ocr_pipeline(file_path)
        return result.to_dict()
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)