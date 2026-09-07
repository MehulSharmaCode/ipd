# backend/app/document_processing/interfaces.py
"""
Document Processor Interface
==============================
Defines the protocol that every document processor must implement.

Using typing.Protocol so processors don't need to inherit from a base class —
they just need to have the right method signature (structural subtyping).

Any new document type only needs:
  1. A class with a `process(file_path, doc_type) -> ExtractionResult` method.
  2. Registration in the DocumentRouter.
"""

from typing import Protocol, runtime_checkable

from app.document_processing.schemas import ExtractionResult


@runtime_checkable
class DocumentProcessor(Protocol):
    """
    Protocol for all document processors.

    Every processor receives a file path and the declared document type,
    and returns a standardised ExtractionResult.
    """

    def process(self, file_path: str, doc_type: str) -> ExtractionResult:
        """
        Process an uploaded document and extract structured fields.

        Args:
            file_path: Absolute path to the saved file on disk.
            doc_type:  The document type hint from the user
                       (e.g. "aadhar", "pan", "7_12").

        Returns:
            ExtractionResult with all extracted fields, validation info,
            and processing metadata.
        """
        ...
