"""
OCR Service
-----------
Responsibility: Execute Tesseract OCR and return extracted text + confidence.

IMPORTANT: This module imports app.ml.ocr.config FIRST, which:
  - Auto-detects the Tesseract executable (env var → PATH → platform defaults)
  - Verifies the binary actually executes
  - Sets TESSDATA_PREFIX in the environment
  - Configures pytesseract.tesseract_cmd

This ensures the correct path is set even if the old ocr_engine*.py files
are imported elsewhere (they set a Windows path at module level).
"""

import os
import time
import logging
from typing import Optional
import numpy as np
import fitz  # PyMuPDF
import pytesseract

# ── MUST be imported BEFORE any pytesseract calls ─────────────────────────────
# This sets pytesseract.tesseract_cmd and TESSDATA_PREFIX via the config module.
from app.ml.ocr import config as _ocr_config

from app.ml.ocr.preprocessing import preprocess, preprocess_grayscale, preprocess_pdf_page

logger = logging.getLogger(__name__)

# ── Apply the detected path to pytesseract ────────────────────────────────────
# This is done HERE (not in config.py) to keep pytesseract coupling in one place.
# This call overwrites any Windows path set by the legacy ocr_engine*.py files.
if _ocr_config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _ocr_config.TESSERACT_CMD
    logger.info(
        f"pytesseract.tesseract_cmd → '{pytesseract.pytesseract.tesseract_cmd}' "
        f"({_ocr_config.DETECTION_METHOD})"
    )
else:
    logger.error(
        "OCR Service: Tesseract is NOT available. "
        "All OCR calls will fail. "
        "Set the TESSERACT_PATH environment variable or install Tesseract."
    )

# ── Tesseract OCR configuration flags ─────────────────────────────────────────
# We try multiple PSM modes and use the result with the most extracted text.
# PSM 6 = single uniform block of text (default — good for Aadhaar)
# PSM 11 = sparse text, finds as much text as possible (better for PAN cards)
# PSM 3 = fully auto page segmentation (good fallback)
_TESSERACT_CONFIGS = [
    "--oem 3 --psm 6",   # Primary: uniform block
    "--oem 3 --psm 11",  # Fallback: sparse text (better for PAN)
    "--oem 3 --psm 3",   # Fallback: auto layout
]


class OCRResult:
    """Structured result from the OCR service."""

    def __init__(self, text: str, confidence: float, processing_time_ms: float):
        self.text = text
        self.confidence = confidence          # Average confidence 0–100
        self.processing_time_ms = processing_time_ms

    def __repr__(self):
        return (
            f"OCRResult(confidence={self.confidence:.1f}%, "
            f"time={self.processing_time_ms:.0f}ms, "
            f"text_len={len(self.text)})"
        )


def _ensure_tesseract_ready():
    """
    Guard: raise a clear RuntimeError if Tesseract is not configured.
    Called at the start of every OCR operation.
    """
    if not _ocr_config.TESSERACT_AVAILABLE:
        summary = _ocr_config.get_config_summary()
        raise RuntimeError(
            f"Tesseract OCR engine is not available.\n"
            f"Detection method tried: {summary['detection_method']}\n"
            f"Platform: {summary['platform']} / {summary['machine']}\n"
            f"To fix: set the TESSERACT_PATH environment variable, or install Tesseract:\n"
            f"  macOS:  brew install tesseract\n"
            f"  Ubuntu: sudo apt install tesseract-ocr\n"
            f"Then restart the server."
        )


def _run_tesseract(preprocessed_image: np.ndarray) -> OCRResult:
    """
    Run Tesseract on a preprocessed numpy array.
    Tries multiple PSM modes and returns the one with the most text extracted.
    This multi-PSM strategy significantly improves PAN card extraction where
    the single-block PSM 6 often misses text in mixed-layout regions.
    """
    _ensure_tesseract_ready()
    start = time.monotonic()

    # Re-apply the correct path on every call to guard against import-order
    # issues where another module may have overwritten tesseract_cmd
    if _ocr_config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = _ocr_config.TESSERACT_CMD

    best_text = ""
    best_confidence = 0.0

    for config in _TESSERACT_CONFIGS:
        try:
            # Get confidence data
            data = pytesseract.image_to_data(
                preprocessed_image,
                config=config,
                output_type=pytesseract.Output.DICT,
            )
            confidences = [int(c) for c in data["conf"] if int(c) > 0]
            avg_confidence = float(sum(confidences) / len(confidences)) if confidences else 0.0

            # Get full text
            text = pytesseract.image_to_string(preprocessed_image, config=config)

            # Keep whichever PSM produces the most text content
            # (more text = more data available for field extraction)
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                best_confidence = avg_confidence
                logger.debug(f"OCR: PSM config '{config}' produced {len(text)} chars @ {avg_confidence:.1f}%")

        except pytesseract.TesseractNotFoundError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            raise RuntimeError(
                f"pytesseract raised TesseractNotFoundError even though "
                f"tesseract_cmd='{pytesseract.pytesseract.tesseract_cmd}'. "
                f"This usually means the binary exists but cannot be executed by the OS. "
                f"Check file permissions. Original error: {exc}"
            )
        except Exception as e:
            logger.warning(f"OCR: PSM config '{config}' failed: {e} — trying next config")
            continue

    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        f"OCR: best_confidence={best_confidence:.1f}%, "
        f"chars={len(best_text)}, time={elapsed_ms:.0f}ms"
    )
    return OCRResult(text=best_text, confidence=best_confidence, processing_time_ms=elapsed_ms)


def extract_from_image(file_path: str) -> OCRResult:
    """
    Preprocess an image file and run multi-pass OCR.
    Tries both adaptive thresholding and contrast-enhanced grayscale passes,
    selecting the result with highest text yield and confidence.
    """
    logger.info(f"OCR: processing image '{os.path.basename(file_path)}'")
    
    # Pass 1: Adaptive thresholding
    preprocessed_bin = preprocess(file_path)
    result_bin = _run_tesseract(preprocessed_bin)

    # Pass 2: Enhanced grayscale (crucial for shadowed/watermarked ID cards)
    try:
        preprocessed_gray = preprocess_grayscale(file_path)
        result_gray = _run_tesseract(preprocessed_gray)

        # Pick whichever pass yields more text content
        if len(result_gray.text.strip()) > len(result_bin.text.strip()):
            logger.info("OCR: Grayscale pass yielded superior text output!")
            return result_gray
    except Exception as e:
        logger.warning(f"OCR grayscale pass failed: {e}")

    return result_bin


def extract_from_pdf(file_path: str) -> OCRResult:
    """
    Check for embedded text layer (digital vector PDF) first for instant 100% accurate extraction,
    falling back to image OCR if the PDF contains scanned page images.
    """
    logger.info(f"OCR: processing PDF '{os.path.basename(file_path)}'")
    doc = fitz.open(file_path)
    
    # ── Fast path: check for digital text layer (e.g. Mahabhumi Digital 7/12 PDFs) ──
    digital_text_blocks = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if text and len(text.strip()) > 30:
            digital_text_blocks.append(text.strip())

    if digital_text_blocks and len(digital_text_blocks) == len(doc):
        combined_text = "\n".join(digital_text_blocks)
        doc.close()
        logger.info(f"OCR: PyMuPDF digital text layer found! Extracted {len(combined_text)} chars directly.")
        return OCRResult(text=combined_text, confidence=99.0, processing_time_ms=5.0)

    # ── Fallback: scanned image rendering + Tesseract OCR ──
    all_texts = []
    all_confidences = []
    total_ms = 0.0

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat)
        preprocessed = preprocess_pdf_page(pix)
        result = _run_tesseract(preprocessed)
        all_texts.append(result.text)
        all_confidences.append(result.confidence)
        total_ms += result.processing_time_ms
        logger.debug(f"PDF page {page_num + 1}: confidence={result.confidence:.1f}%")

    doc.close()

    combined_text = "\n".join(all_texts)
    avg_confidence = float(sum(all_confidences) / len(all_confidences)) if all_confidences else 0.0
    return OCRResult(text=combined_text, confidence=avg_confidence, processing_time_ms=total_ms)


def extract_text(file_path: str) -> OCRResult:
    """
    Auto-detect file type and run OCR. Primary public API of the OCR service.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_from_pdf(file_path)
    elif ext in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}:
        return extract_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file extension: '{ext}'")


def verify_tesseract() -> dict:
    """
    Return a diagnostic summary of the OCR engine status.
    Used by the /api/monitoring/ocr-health endpoint.
    """
    return _ocr_config.get_config_summary()
