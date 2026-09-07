# backend/app/document_processing/vision/__init__.py
"""
Vision Processors — Registration
===================================
Imports the Gemini 7/12 pipeline and registers it with the global
DocumentRouter.

Importing this package makes 7/12 processing available through:
    document_router.route(file_path, "7_12")

NOTE: The Gemini client is lazily initialised — importing this module
does NOT trigger an API call or require GEMINI_API_KEY to be set
(it only fails at runtime when a 7/12 upload is actually processed).
"""

from app.document_processing.router import document_router
from app.document_processing.vision.gemini_pipeline import Satbara712Processor

# Register the 7/12 processor. "satbara" / "satbara_7_12" are legacy aliases
# from the pre-document_processing upload flow — kept so older clients don't
# get an "unsupported document type" error. ("7/12" is normalized to "7_12"
# by the upload endpoint before routing, so no separate alias is needed.)
_satbara_processor = Satbara712Processor()
document_router.register("7_12", _satbara_processor)
document_router.register("satbara", _satbara_processor)
document_router.register("satbara_7_12", _satbara_processor)
