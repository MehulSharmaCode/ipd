"""
Centralized OCR Configuration
==============================
This is the SINGLE SOURCE OF TRUTH for all Tesseract configuration.

Import this module BEFORE pytesseract is called anywhere.
All other OCR modules must import `TESSERACT_CMD` from here.

Detection priority:
  1. TESSERACT_PATH environment variable (explicit override)
  2. shutil.which("tesseract") — searches PATH + known macOS Homebrew locations
  3. Known platform-specific defaults (macOS Apple Silicon, macOS Intel, Linux)
  4. Fail with detailed diagnostics

This approach is robust against:
  - Virtual environments that don't inherit shell PATH
  - macOS Gatekeeper and SIP restrictions
  - Different Homebrew prefixes (Apple Silicon vs Intel Mac)
  - Docker / containerized environments
  - CI/CD pipelines
"""

import os
import shutil
import subprocess
import platform
import logging

logger = logging.getLogger(__name__)

# ── Known platform defaults ────────────────────────────────────────────────────
_PLATFORM_DEFAULTS = {
    "Darwin": [
        "/opt/homebrew/bin/tesseract",   # macOS Apple Silicon (M-series)
        "/usr/local/bin/tesseract",      # macOS Intel (Homebrew)
        "/opt/local/bin/tesseract",      # MacPorts
    ],
    "Linux": [
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/snap/bin/tesseract",
    ],
    "Windows": [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ],
}

# ── Tessdata prefix defaults ───────────────────────────────────────────────────
_TESSDATA_DEFAULTS = {
    "Darwin": [
        "/opt/homebrew/share/tessdata",   # Apple Silicon Homebrew
        "/usr/local/share/tessdata",      # Intel Homebrew
        "/opt/local/share/tessdata",      # MacPorts
    ],
    "Linux": [
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/tessdata",
        "/usr/local/share/tessdata",
    ],
}


def _find_tesseract_executable() -> tuple[str | None, str]:
    """
    Find the Tesseract executable using a multi-strategy approach.

    Returns:
        (path, reason) — path is None if not found, reason explains how it was found
                         (or why it failed).
    """
    # Strategy 1: Explicit environment variable override
    env_path = os.environ.get("TESSERACT_PATH", "").strip()
    if env_path:
        if os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path, f"Environment variable TESSERACT_PATH={env_path}"
        else:
            logger.warning(
                f"TESSERACT_PATH env var is set to '{env_path}' "
                "but the file is not accessible. Falling through to auto-detection."
            )

    # Strategy 2: shutil.which — searches the process PATH + extended macOS paths
    # Augment the search PATH to include Homebrew locations that may be absent
    # from uvicorn's subprocess environment
    search_path = os.environ.get("PATH", "")
    extra_dirs = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin", "/usr/bin"]
    for d in extra_dirs:
        if d not in search_path:
            search_path = d + os.pathsep + search_path

    found = shutil.which("tesseract", path=search_path)
    if found:
        return found, f"Discovered via which/PATH: {found}"

    # Strategy 3: Check known platform-specific default paths
    system = platform.system()
    for candidate in _PLATFORM_DEFAULTS.get(system, []):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate, f"Platform default ({system}): {candidate}"

    return None, (
        f"Tesseract not found. Tried: env TESSERACT_PATH, PATH search, "
        f"platform defaults for '{system}'. "
        "Install via: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)"
    )


def _find_tessdata_prefix() -> str | None:
    """Find the tessdata directory for the current Tesseract installation."""
    # Explicit environment variable takes priority
    env_prefix = os.environ.get("TESSDATA_PREFIX", "").strip()
    if env_prefix and os.path.isdir(env_prefix):
        return env_prefix

    system = platform.system()
    for candidate in _TESSDATA_DEFAULTS.get(system, []):
        if os.path.isdir(candidate):
            return candidate

    return None


def _verify_executable(path: str) -> tuple[bool, str]:
    """
    Verify that the Tesseract binary actually executes correctly.
    Returns (success, version_string).
    """
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # tesseract --version writes to stderr on older versions
        version_output = result.stdout or result.stderr
        first_line = version_output.strip().split("\n")[0]
        return True, first_line
    except FileNotFoundError:
        return False, f"FileNotFoundError: '{path}' cannot be executed by the OS"
    except PermissionError:
        return False, f"PermissionError: no execute permission on '{path}'"
    except subprocess.TimeoutExpired:
        return False, f"Timeout: '{path} --version' took longer than 10s"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# ── Run detection at module import time ───────────────────────────────────────
_tesseract_path, _detection_reason = _find_tesseract_executable()
_tessdata_prefix = _find_tessdata_prefix()
_verified = False
_version = None

if _tesseract_path:
    _ok, _version = _verify_executable(_tesseract_path)
    if _ok:
        _verified = True
        # Set TESSDATA_PREFIX so the subprocess started by pytesseract can find languages
        if _tessdata_prefix and "TESSDATA_PREFIX" not in os.environ:
            os.environ["TESSDATA_PREFIX"] = _tessdata_prefix
        logger.info(
            f"✅ Tesseract configured: path='{_tesseract_path}' | "
            f"version={_version} | tessdata={_tessdata_prefix} | "
            f"source={_detection_reason}"
        )
    else:
        logger.error(
            f"❌ Tesseract found at '{_tesseract_path}' but FAILED to execute: {_version}"
        )
        _tesseract_path = None  # Treat as not found
else:
    logger.error(f"❌ Tesseract NOT found. {_detection_reason}")


# ── Public API ────────────────────────────────────────────────────────────────

#: The resolved, verified absolute path to the tesseract binary.
#: None if tesseract is not available.
TESSERACT_CMD: str | None = _tesseract_path

#: True if tesseract was found AND successfully executed during startup.
TESSERACT_AVAILABLE: bool = _verified

#: Human-readable version string (e.g., "tesseract 5.5.2")
TESSERACT_VERSION: str | None = _version

#: The tessdata directory path (or None if not found)
TESSDATA_PREFIX: str | None = _tessdata_prefix

#: How the executable was found (for diagnostics)
DETECTION_METHOD: str = _detection_reason


def get_config_summary() -> dict:
    """Return a diagnostic summary of the OCR configuration."""
    return {
        "tesseract_cmd": TESSERACT_CMD,
        "tesseract_available": TESSERACT_AVAILABLE,
        "version": TESSERACT_VERSION,
        "tessdata_prefix": TESSDATA_PREFIX,
        "detection_method": DETECTION_METHOD,
        "platform": platform.system(),
        "machine": platform.machine(),
        "env_TESSERACT_PATH": os.environ.get("TESSERACT_PATH", "(not set)"),
        "env_TESSDATA_PREFIX": os.environ.get("TESSDATA_PREFIX", "(not set)"),
    }
