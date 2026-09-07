"""
Connectivity Test — Gemini (Configurable Model)
=================================================
Standalone script to verify that the Gemini API key is valid
and the model is reachable before running the full PoC.

Reads from backend/.env:
  GEMINI_API_KEY  — required
  GEMINI_MODEL    — optional, defaults to gemini-2.0-flash

Usage:
    cd backend
    source .venv/bin/activate
    python -m poc_document_ai.connectivity_test
"""

import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from backend/ root (works regardless of where script is invoked)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent
_env_path = _backend_dir / ".env"
load_dotenv(dotenv_path=_env_path)

DEFAULT_MODEL = "gemini-2.0-flash"


def run_connectivity_test() -> bool:
    """
    1. Verify GEMINI_API_KEY is present.
    2. Read GEMINI_MODEL (or use default).
    3. Initialize the Gemini client.
    4. Send a trivial prompt and check the response.

    Returns True on success, False on failure.
    """

    # ── Step 1: Key presence ──────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("✗ GEMINI_API_KEY is missing or empty in", _env_path)
        print("  Add it to backend/.env and try again.")
        return False

    print(f"✓ GEMINI_API_KEY loaded ({len(api_key)} chars, ending …{api_key[-4:]})")

    # ── Step 2: Model name ────────────────────────────────────────────────
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    print(f"✓ GEMINI_MODEL = {model}")

    # ── Step 3: SDK import ────────────────────────────────────────────────
    try:
        from google import genai
    except ImportError:
        print("✗ google-genai SDK is not installed.")
        print("  Run: pip install google-genai")
        return False

    print("✓ google-genai SDK imported successfully")

    # ── Step 4: Initialize client ─────────────────────────────────────────
    try:
        client = genai.Client(api_key=api_key)
    except Exception as exc:
        print(f"✗ Failed to create Gemini client: {exc}")
        return False

    print("✓ Gemini client created")

    # ── Step 5: Send test prompt ──────────────────────────────────────────
    print(f"  Sending test prompt to {model} …")
    start = time.time()

    try:
        response = client.models.generate_content(
            model=model,
            contents="Reply ONLY with the single word: CONNECTED",
        )
        elapsed = time.time() - start
        text = response.text.strip()

        if "CONNECTED" in text.upper():
            print(f"✓ Gemini Connected Successfully  (response: \"{text}\", {elapsed:.2f}s)")
            return True
        else:
            print(f"⚠ Unexpected response: \"{text}\"  ({elapsed:.2f}s)")
            print("  The API is reachable but the response was unexpected.")
            return True  # still connected, just a surprising answer

    except Exception as exc:
        elapsed = time.time() - start
        print(f"✗ Gemini API call failed after {elapsed:.2f}s")
        print(f"  Error: {exc}")

        # Provide actionable guidance for common errors
        err_str = str(exc)
        if "404" in err_str and "no longer available" in err_str.lower():
            print()
            print("  ╔══════════════════════════════════════════════════════════╗")
            print("  ║  MODEL DEPRECATED — update GEMINI_MODEL in backend/.env ║")
            print("  ║                                                          ║")
            print("  ║  Try one of:                                             ║")
            print("  ║    GEMINI_MODEL=gemini-2.0-flash                         ║")
            print("  ║    GEMINI_MODEL=gemini-3.5-flash                         ║")
            print("  ║    GEMINI_MODEL=gemini-3.6-flash                         ║")
            print("  ╚══════════════════════════════════════════════════════════╝")
        elif "403" in err_str:
            print("  → Authentication failed. Check your GEMINI_API_KEY.")
        elif "429" in err_str:
            print("  → Rate limited. Wait a moment and try again.")

        return False


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Gemini — Connectivity Test")
    print("=" * 60)
    print()

    success = run_connectivity_test()

    print()
    if success:
        print("═" * 60)
        print("  RESULT: PASS — ready to run the full PoC")
        print("═" * 60)
    else:
        print("═" * 60)
        print("  RESULT: FAIL — fix the issue above before continuing")
        print("═" * 60)
        sys.exit(1)
