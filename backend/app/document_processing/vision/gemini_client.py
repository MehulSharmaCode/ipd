# backend/app/document_processing/vision/gemini_client.py
"""
Production Gemini Client
==========================
Handles all communication with Google Gemini for vision-based document
understanding.

Ported from the validated PoC (poc_document_ai/gemini_client.py).
Key differences from PoC:
  - Reads config from app.core.config (via Settings), not standalone .env
  - Structured as a singleton for request-reuse
  - Import-safe: does not crash if GEMINI_API_KEY is missing (logs warning)
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

# Ensure .env is loaded (config.py also does this, but be defensive)
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
_env_path = _backend_dir / ".env"
load_dotenv(dotenv_path=_env_path)

DEFAULT_MODEL = "gemini-flash-latest"


class GeminiClient:
    """
    Wrapper around the Google GenAI SDK for vision-based extraction.

    Reads GEMINI_API_KEY and GEMINI_MODEL from environment variables.
    Reuses the same client instance across requests.
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

    def extract_fields(self, image_path: str, prompt: str) -> dict:
        """
        Send an image + extraction prompt to Gemini.
        Attempts to parse the response as JSON.

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

        parsed, parse_error = self._try_parse_json(result["text"])
        result["json"] = parsed
        result["raw_text"] = result.pop("text")
        if parse_error:
            result["error"] = parse_error
            result["success"] = parsed is not None

        return result

    def analyze_document(self, image_path: str, prompt: str) -> dict:
        """Send an image + analysis prompt. Returns raw text response."""
        result = self._send(image_path, prompt)
        result["raw_text"] = result.pop("text", "")
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(self, image_path: str, prompt: str) -> dict:
        path = Path(image_path)
        if not path.exists():
            return {
                "text": "",
                "elapsed_seconds": 0.0,
                "success": False,
                "error": f"Image file not found: {image_path}",
            }

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
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            elif lines[0].strip().startswith("```"):
                lines = lines[1:]
            cleaned = "\n".join(lines).strip()
        cleaned = cleaned.lstrip("\ufeff")

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed, None
            return None, f"Expected JSON object, got {type(parsed).__name__}"
        except json.JSONDecodeError as exc:
            return None, f"JSON parse error: {exc}"
