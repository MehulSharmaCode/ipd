"""
Image Preprocessing Module
--------------------------
Responsibility: Transform raw images into high-quality inputs for OCR.
The OCR service NEVER receives a raw image — all input goes through this module first.

Supported inputs:
  - File path (str) to JPEG/PNG image
  - OpenCV numpy array (BGR)
  - PyMuPDF Pixmap (converted internally)
"""

import logging
import numpy as np
import cv2
from typing import Union

logger = logging.getLogger(__name__)


def _ensure_bgr(image_input: Union[str, np.ndarray]) -> np.ndarray:
    """Load or validate the image into an OpenCV BGR numpy array."""
    if isinstance(image_input, str):
        image = cv2.imread(image_input)
        if image is None:
            raise ValueError(f"Could not load image from path: {image_input}")
        return image
    elif isinstance(image_input, np.ndarray):
        return image_input
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Correct skew/rotation in a grayscale image using Hough line detection.
    Returns the corrected grayscale image.
    """
    try:
        # Detect edges and find lines
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        if lines is None:
            return gray

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                angles.append(angle)

        if not angles:
            return gray

        # Only correct if skew is meaningful (ignore near-zero angles)
        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5 or abs(median_angle) > 45:
            return gray

        h, w = gray.shape
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        deskewed = cv2.warpAffine(
            gray, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        logger.debug(f"Deskewed image by {median_angle:.2f} degrees")
        return deskewed
    except Exception as e:
        logger.warning(f"Deskew failed, returning original: {e}")
        return gray


def preprocess(image_input: Union[str, np.ndarray], enhance_resolution: bool = True) -> np.ndarray:
    """
    Main preprocessing function. Applies the full pipeline:
      1. Load to BGR numpy array
      2. Resolution enhancement (upscale if beneficial)
      3. Grayscale conversion
      4. Deskew correction
      5. Bilateral noise removal (preserves edges)
      6. Adaptive thresholding (handles uneven lighting)
      7. Morphological cleanup (remove speckles)
      8. Border cleanup

    Returns a binary (thresholded) numpy array ready for Tesseract.
    """
    image = _ensure_bgr(image_input)
    h, w = image.shape[:2]

    # 1. Resolution enhancement — upscale small/low-res images
    if enhance_resolution:
        # Target at least 300 DPI equivalent: typical ID card is ~85×54mm → 1000×630 at 300dpi
        scale = 1.0
        if w < 1000 or h < 600:
            scale = max(1000 / w, 600 / h, 1.5)
        if scale > 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            logger.debug(f"Upscaled image {w}x{h} → {new_w}x{new_h} (scale={scale:.2f})")

    # 2. Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 3. Deskew
    gray = _deskew(gray)

    # 4. Bilateral filter: removes noise while keeping edges sharp
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # 5. Adaptive thresholding: handles documents with shadows / gradient backgrounds
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11, C=2
    )

    # 6. Morphological opening: removes tiny speckles (salt noise)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # 7. Border cleanup: add a white border to avoid Tesseract misreading edges
    cleaned = cv2.copyMakeBorder(cleaned, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

    return cleaned


def preprocess_pdf_page(pixmap) -> np.ndarray:
    """
    Preprocess a PyMuPDF Pixmap (from a PDF page).
    Converts it to a numpy array and runs the standard preprocessing pipeline.
    """
    n = pixmap.n  # number of channels
    img_data = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.h, pixmap.w, n)

    if n == 3:
        img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
    elif n == 4:
        img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
    else:
        img_bgr = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)

    return preprocess(img_bgr, enhance_resolution=False)  # PDF pages already at high res
