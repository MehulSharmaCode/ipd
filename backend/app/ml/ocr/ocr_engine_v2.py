import pytesseract
import cv2
import numpy as np
import fitz  # PyMuPDF
import os
import re
from typing import Dict, Any, List

# NOTE: Tesseract path is configured in app.ml.ocr.config — do NOT set tesseract_cmd here.
# The old Windows path has been removed to prevent breaking macOS/Linux deployments.
# app.ml.ocr.ocr_service imports config.py which correctly detects the binary.


class OCREngineV2:
    def __init__(self):
        # Keywords for classification
        self.AADHAAR_KEYWORDS = ["GOVERNMENT OF INDIA", "UNIQUE IDENTIFICATION", "MALE", "FEMALE", "AADHAAR", "DOB", "YEAR OF BIRTH", "ENROLLMENT"]
        self.PAN_KEYWORDS = ["INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "FATHER'S NAME", "SIGNATURE", "GOVT. OF INDIA"]

    def preprocess_image(self, image_input):
        """Standard image preprocessing for OCR."""
        if isinstance(image_input, str):
            image = cv2.imread(image_input)
            if image is None:
                raise ValueError(f"Image not found: {image_input}")
        else:
            image = image_input

        # 1. Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 2. Resizing (upscale slightly for smaller text)
        gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        
        # 3. Adaptive Thresholding for varied lighting
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 4. Noise reduction
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        
        return denoised

    def _extract_text_from_file(self, file_path: str) -> str:
        """Determines file type and extracts raw text."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self._pdf_to_text(file_path)
        else:
            return self._image_to_text(file_path)

    def _image_to_text(self, image_path: str) -> str:
        processed = self.preprocess_image(image_path)
        return pytesseract.image_to_string(processed, config='--oem 3 --psm 6')

    def _pdf_to_text(self, pdf_path: str) -> str:
        text_results = []
        doc = fitz.open(pdf_path)
        for page in doc:
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            # Use OpenCV for consistency
            if pix.n >= 3:
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR if pix.n == 3 else cv2.COLOR_RGBA2BGR)
                processed = self.preprocess_image(img_bgr)
                page_text = pytesseract.image_to_string(processed, config='--oem 3 --psm 6')
                text_results.append(page_text)
        doc.close()
        return "\n".join(text_results)

    def verify_document(self, file_path: str, expected_type: str) -> Dict[str, Any]:
        """
        Main entry point for advanced verification.
        Determines if the document actually is what it claims to be.
        """
        raw_text = self._extract_text_from_file(file_path)
        normalized_text = raw_text.upper()
        
        result = {
            "is_valid": False,
            "extracted_id": None,
            "doc_type": None,
            "confidence": 0,
            "raw_text_snippet": raw_text[:200]
        }

        # 1. Document Classification
        aadhar_hits = sum(1 for k in self.AADHAAR_KEYWORDS if k in normalized_text)
        pan_hits = sum(1 for k in self.PAN_KEYWORDS if k in normalized_text)
        
        # Determine actual type based on hits
        actual_type = "aadhar" if aadhar_hits > pan_hits else "pan"
        if aadhar_hits == 0 and pan_hits == 0:
            actual_type = "unknown"

        # 2. Strict Type Check
        if expected_type.lower() != actual_type:
            return {**result, "error": f"Document mismatch. Expected {expected_type}, but looks like {actual_type}."}

        # 3. ID Extraction & Validation
        if actual_type == "aadhar":
            # Regex for 12 digits (handles spaces and hyphens)
            match = re.search(r"(\d{4})[\s-]*(\d{4})[\s-]*(\d{4})", normalized_text)
            if match:
                id_val = "".join(match.groups())
                from app.ml.ocr.utils import validate_aadhar
                if validate_aadhar(id_val):
                    result["is_valid"] = True
                    result["extracted_id"] = id_val
                    result["doc_type"] = "aadhar"
                    result["confidence"] = 0.95
                else:
                    result["error"] = "Invalid Aadhaar checksum (Verhoeff fail)."
            else:
                result["error"] = "No valid 12-digit Aadhaar pattern found."
                
        elif actual_type == "pan":
            match = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", normalized_text)
            if match:
                result["is_valid"] = True
                result["extracted_id"] = match.group()
                result["doc_type"] = "pan"
                result["confidence"] = 0.90
            else:
                result["error"] = "No valid PAN pattern found."

        return result
