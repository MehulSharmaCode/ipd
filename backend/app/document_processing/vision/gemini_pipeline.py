# backend/app/document_processing/vision/gemini_pipeline.py
"""
Gemini 7/12 Pipeline
======================
Implements the DocumentProcessor interface for Maharashtra 7/12 documents.

This pipeline:
  1. Sends the uploaded image to Gemini with the extraction prompt.
  2. Parses the JSON response.
  3. Maps Gemini's output to the standardised ExtractionResult schema.
  4. Validates the extracted fields.

Ported from the validated PoC (poc_document_ai/run_poc.py).
"""

import time
import logging
from typing import Optional

from app.document_processing.schemas import ExtractionResult
from app.document_processing.vision.gemini_client import GeminiClient
from app.document_processing.vision.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class Satbara712Processor:
    """
    DocumentProcessor for Maharashtra 7/12 (Satbara) documents.

    Uses Gemini Vision to understand handwritten Marathi land records
    and extract structured agricultural information.
    """

    def __init__(self):
        self._client: Optional[GeminiClient] = None

    def _get_client(self) -> GeminiClient:
        """Lazy-initialise the Gemini client on first use."""
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    def process(self, file_path: str, doc_type: str) -> ExtractionResult:
        start = time.monotonic()

        # Initialise client (lazy — only on first call)
        try:
            client = self._get_client()
        except RuntimeError as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error("Gemini client init failed: %s", e)
            return ExtractionResult.make_error("7_12", str(e), elapsed_ms)

        # Send image to Gemini
        response = client.extract_fields(file_path, EXTRACTION_PROMPT)
        elapsed_ms = (time.monotonic() - start) * 1000

        if not response["success"]:
            logger.error("Gemini extraction failed: %s", response.get("error"))
            return ExtractionResult.make_error(
                "7_12", response.get("error", "Unknown Gemini error"), elapsed_ms
            )

        gemini_json = response.get("json")
        if gemini_json is None:
            return ExtractionResult.make_error(
                "7_12",
                f"Failed to parse Gemini response as JSON: {response.get('error')}",
                elapsed_ms,
            )

        # Build standardised ExtractionResult from Gemini's output
        result = self._map_to_extraction_result(gemini_json, elapsed_ms)

        logger.info(
            "Satbara712Processor: extracted %d fields in %.0fms",
            len(result.fields), elapsed_ms,
        )
        return result

    def _map_to_extraction_result(self, data: dict,
                                   elapsed_ms: float) -> ExtractionResult:
        """
        Map Gemini's raw JSON output to the standardised ExtractionResult.

        The Gemini prompt returns a flat dict with keys like 'owner_name',
        'survey_number', etc. We wrap each into an ExtractedField with
        source_document='7_12'.

        Confidence is set to 0.85 (the validated PoC baseline) for populated
        fields and 0.0 for null fields.
        """
        result = ExtractionResult(
            document_type="7_12",
            success=True,
            processing_time_ms=elapsed_ms,
        )

        # Direct field mappings (Gemini key → standardised key)
        FIELD_MAP = {
            "owner_name": "owner_name",
            "survey_number": "survey_number",
            "gat_number": "gat_number",
            "village": "village",
            "taluka": "taluka",
            "district": "district",
            "land_area": "land_area",
            "current_crop": "current_crop",
            "irrigation": "irrigation",
            "soil_type": "soil_type",
            "ownership_type": "ownership_type",
        }

        for gemini_key, standard_key in FIELD_MAP.items():
            value = data.get(gemini_key)
            if value is not None and value != "":
                result.set_field(standard_key, value, confidence=0.85)

        # Extract additional_info sub-fields and flatten them
        additional = data.get("additional_info")
        if isinstance(additional, dict):
            if additional.get("co_owners"):
                result.set_field("co_owners", additional["co_owners"], confidence=0.80)
            if additional.get("mutation_entries") is not None:
                result.set_field("mutation_entries", additional["mutation_entries"], confidence=0.70)
            if additional.get("hissa_number") is not None:
                result.set_field("hissa_number", additional["hissa_number"], confidence=0.75)
            if additional.get("pot_hissa") is not None:
                result.set_field("pot_hissa", additional["pot_hissa"], confidence=0.70)
            if additional.get("land_use"):
                result.set_field("land_use", additional["land_use"], confidence=0.85)
            if additional.get("season"):
                result.set_field("season", additional["season"], confidence=0.80)

        # Validation
        warnings = []
        if not result.get_value("owner_name"):
            warnings.append("Owner name could not be extracted.")
        if not result.get_value("survey_number") and not result.get_value("gat_number"):
            warnings.append("Neither survey number nor gat number could be extracted.")
        if not result.get_value("village"):
            warnings.append("Village name could not be extracted.")

        result.validation = {
            "valid": len(warnings) == 0,
            "warnings": warnings,
        }

        return result
