from app.ml.ocr.document_parser import DocumentParser
from app.ml.ocr.ocr_engine import OCREngine

ocr = OCREngine()
parser = DocumentParser()

text = ocr.extract_text("Vinit adharCard.jpg")

print("OCR TEXT:\n", text)

aadhar = parser.extract_aadhar(text)

print("\nExtracted Aadhaar:", aadhar)