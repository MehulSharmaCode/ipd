import pytesseract
import cv2
import numpy as np
import fitz # PyMuPDF
import os

# NOTE: Tesseract path is configured in app.ml.ocr.config — do NOT set tesseract_cmd here.
# The old Windows path below has been removed to prevent breaking macOS/Linux deployments.


class OCREngine:

    def preprocess_image(self, image_input):
        """
        Preprocess image for better OCR. 
        Accepts either a file path (str) or an already loaded cv2 image (numpy array).
        """
        if isinstance(image_input, str):
            image = cv2.imread(image_input)
            if image is None:
                raise ValueError(f"Image not found: {image_input}")
        else:
            image = image_input

        # resize for better OCR
        image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # remove noise
        gray = cv2.bilateralFilter(gray, 9, 75, 75)

        # threshold
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        return thresh


    def extract_text(self, file_path: str):
        """
        Extract text from an image or PDF file.
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._extract_from_pdf(file_path)
        else:
            return self._extract_from_image(file_path)

    def _extract_from_image(self, image_path: str):
        processed = self.preprocess_image(image_path)
        # Tesseract configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed, config=custom_config)
        return text

    def _extract_from_pdf(self, pdf_path: str):
        """
        Convert PDF pages to images and run OCR on each.
        """
        text_results = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Increase resolution (zoom) for better OCR accuracy
            zoom = 2.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert pixmap to numpy array for OpenCV
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            # Convert RGB to BGR for OpenCV
            if pix.n == 3: # RGB
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            elif pix.n == 4: # RGBA
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            else:
                img_bgr = img_data # Grayscale or other
                
            processed = self.preprocess_image(img_bgr)
            custom_config = r'--oem 3 --psm 6'
            page_text = pytesseract.image_to_string(processed, config=custom_config)
            text_results.append(page_text)
            
        doc.close()
        return "\n".join(text_results)