"""
Gemini Client — Isolated Wrapper
==================================
Handles all communication with Google Gemini (configurable model).

This module is COMPLETELY ISOLATED from the main application.
It does NOT import anything from app/.

Configuration (read from backend/.env):
  GEMINI_API_KEY  — required, Google AI Studio API key
  GEMINI_MODEL    — optional, defaults to 'gemini-2.0-flash'

Responsibilities:
  - Load API key and model name from backend/.env
  - Initialize the google-genai client once
  - Expose methods for document analysis and structured extraction
  - Handle errors, timeouts, and retries gracefully
"""

import os
import json
import time
import base64
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load .env from backend/ root
# ---------------------------------------------------------------------------
_backend_dir = Path(__file__).resolve().parent.parent
_env_path = _backend_dir / ".env"
load_dotenv(dotenv_path=_env_path)


# Default model — used when GEMINI_MODEL is not set in .env
DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiClient:
    """
    Wrapper around the Google GenAI SDK.

    The model is read from GEMINI_MODEL in backend/.env.
    If not set, falls back to DEFAULT_MODEL.

    Usage:
        client = GeminiClient()
        result = client.analyze_document(image_path, analysis_prompt)
        result = client.extract_fields(image_path, extraction_prompt)
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing or empty. "
                f"Add it to {_env_path}"
            )

        self.model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()
        if not self.model:
            self.model = DEFAULT_MODEL

        from google import genai

        self._client = genai.Client(api_key=api_key)
        logger.info("GeminiClient initialised (model=%s)", self.model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_document(self, image_path: str, prompt: str) -> dict:
        """
        Send an image + prompt and return the raw text response plus metadata.

        Returns:
            {
                "text": <raw response text>,
                "elapsed_seconds": <float>,
                "success": <bool>,
                "error": <str or None>,
            }
        """
        return self._send(image_path, prompt)

    def extract_fields(self, image_path: str, prompt: str) -> dict:
        """
        Send an image + extraction prompt.  Attempts to parse the response
        as JSON.

        Returns:
            {
                "json": <parsed dict or None>,
                "raw_text": <raw response text>,
                "elapsed_seconds": <float>,
                "success": <bool>,
                "error": <str or None>,
            }
        """
        result = self._send(image_path, prompt)

        if not result["success"]:
            result["json"] = None
            return result

        # Attempt JSON parse — Gemini may wrap in ```json ... ```
        parsed, parse_error = self._try_parse_json(result["text"])
        result["json"] = parsed
        if parse_error:
            result["error"] = parse_error
            result["success"] = parsed is not None  # partial success if parsed after cleanup

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, image_path: str, prompt: str) -> dict:
        """Send image + prompt to Gemini and return raw result dict."""
        path = Path(image_path)
        if not path.exists():
            return {
                "text": "",
                "elapsed_seconds": 0.0,
                "success": False,
                "error": f"Image file not found: {image_path}",
            }

        # Read image and encode
        image_bytes = path.read_bytes()
        mime_type = self._guess_mime(path)

        start = time.time()
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                                }
                            },
                        ],
                    }
                ],
            )
            elapsed = time.time() - start
            text = response.text.strip() if response.text else ""

            return {
                "text": text,
                "elapsed_seconds": round(elapsed, 3),
                "success": True,
                "error": None,
            }

        except Exception as exc:
            elapsed = time.time() - start
            logger.exception("Gemini API call failed")
            return {
                "text": "",
                "elapsed_seconds": round(elapsed, 3),
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def _guess_mime(path: Path) -> str:
        suffix = path.suffix.lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
        }.get(suffix, "image/jpeg")

    @staticmethod
    def _try_parse_json(text: str) -> tuple[Optional[dict], Optional[str]]:
        """
        Attempt to parse text as JSON.
        Handles common Gemini quirks:
          - Wrapped in ```json ... ```
          - Leading/trailing whitespace
          - BOM characters
        Returns (parsed_dict, error_message).
        """
        cleaned = text.strip()

        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            elif lines[0].strip().startswith("```"):
                lines = lines[1:]
            cleaned = "\n".join(lines).strip()

        # Remove BOM
        cleaned = cleaned.lstrip("\ufeff")

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed, None
            return None, f"Expected JSON object, got {type(parsed).__name__}"
        except json.JSONDecodeError as exc:
            return None, f"JSON parse error: {exc}"
