# backend/app/document_processing/ocr/__init__.py
"""
OCR Processors — Registration
================================
Imports the Aadhaar and PAN adapters and registers them with the
global DocumentRouter.

Importing this package is sufficient to make Aadhaar and PAN processing
available through:
    document_router.route(file_path, "aadhar")
    document_router.route(file_path, "pan")
"""

from app.document_processing.router import document_router
from app.document_processing.ocr.aadhaar import AadhaarProcessor
from app.document_processing.ocr.pan import PANProcessor

# Register adapters with the global router
document_router.register("aadhar", AadhaarProcessor())
document_router.register("aadhaar", AadhaarProcessor())  # alias
document_router.register("pan", PANProcessor())
