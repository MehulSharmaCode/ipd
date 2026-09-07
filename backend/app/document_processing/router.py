# backend/app/document_processing/router.py
"""
Document Router
=================
Routes an uploaded document to the correct processor based on its doc_type.

The upload endpoint calls:
    result = document_router.route(file_path, doc_type)

The router looks up the registered processor and delegates to it.

Adding a new document type:
    1. Implement a class with `process(file_path, doc_type) -> ExtractionResult`.
    2. Call `document_router.register("new_type", YourProcessor())`.

The router is a module-level singleton so processors are registered once
at import time and reused across requests.
"""

import logging
from typing import Optional

from app.document_processing.interfaces import DocumentProcessor
from app.document_processing.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class DocumentRouter:
    """
    Registry + dispatcher for document processors.

    Thread-safe for reads (dict lookup). Registration happens at import time,
    before any request is served, so no lock is needed.
    """

    def __init__(self):
        self._processors: dict[str, DocumentProcessor] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, doc_type: str, processor: DocumentProcessor) -> None:
        """
        Register a processor for a document type.

        Args:
            doc_type:   Canonical type string (e.g. "aadhar", "pan", "7_12").
            processor:  An object implementing the DocumentProcessor protocol.
        """
        key = doc_type.lower().strip()
        self._processors[key] = processor
        logger.info("DocumentRouter: registered processor for '%s' → %s",
                    key, type(processor).__name__)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, file_path: str, doc_type: str) -> ExtractionResult:
        """
        Route a document to the appropriate processor.

        Args:
            file_path: Absolute path to the uploaded file.
            doc_type:  Document type declared by the user.

        Returns:
            ExtractionResult from the matched processor, or an error result
            if no processor is registered for the given doc_type.
        """
        key = doc_type.lower().strip()
        processor = self._processors.get(key)

        if processor is None:
            logger.warning("DocumentRouter: no processor for doc_type='%s'", key)
            return ExtractionResult.make_error(
                document_type=key,
                error_msg=f"Unsupported document type: '{doc_type}'. "
                          f"Supported types: {', '.join(sorted(self._processors.keys()))}",
            )

        logger.info("DocumentRouter: routing '%s' → %s",
                    key, type(processor).__name__)
        return processor.process(file_path, key)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def supported_types(self) -> list[str]:
        """List of currently registered document types."""
        return sorted(self._processors.keys())


# ======================================================================
# Module-level singleton
# ======================================================================
# Processors are registered in Phase 2 (OCR) and Phase 3 (Gemini).
# For now, the router starts empty and is populated at import time
# by the processor modules.

document_router = DocumentRouter()
