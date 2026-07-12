# app/ml/ocr/__init__.py
"""
OCR Package
-----------
IMPORT ORDER IS CRITICAL:
  1. config.py runs first — detects Tesseract, sets TESSDATA_PREFIX
  2. ocr_service.py applies the detected path to pytesseract
  3. pipeline.py is the only public entry point for the rest of the app

Public API:
  from app.ml.ocr.pipeline import process as run_ocr_pipeline
  from app.ml.ocr.ocr_service import verify_tesseract
  from app.ml.ocr.config import TESSERACT_AVAILABLE, get_config_summary
"""

# Step 1: Initialize configuration FIRST (must happen before any pytesseract usage)
from app.ml.ocr import config  # noqa: F401 — side effects: detects Tesseract

# Step 2: Export the public API
from app.ml.ocr.pipeline import process, OCRPipelineResult
from app.ml.ocr.ocr_service import verify_tesseract
from app.ml.ocr.config import TESSERACT_AVAILABLE, get_config_summary

__all__ = [
    "process",
    "OCRPipelineResult",
    "verify_tesseract",
    "TESSERACT_AVAILABLE",
    "get_config_summary",
]
