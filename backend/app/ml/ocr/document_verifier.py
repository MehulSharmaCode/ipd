from app.ml.ocr.ocr_engine import OCREngine
from app.ml.ocr.document_parser import DocumentParser


class DocumentVerifier:

    def __init__(self):

        self.ocr = OCREngine()
        self.parser = DocumentParser()

    def verify_aadhar(self, image_path: str):

        text = self.ocr.extract_text(image_path)

        aadhar = self.parser.extract_aadhar(text)

        return aadhar is not None

    def verify_pan(self, image_path: str):

        text = self.ocr.extract_text(image_path)

        pan = self.parser.extract_pan(text)

        return pan is not None