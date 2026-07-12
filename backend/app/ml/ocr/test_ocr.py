from app.ml.ocr.ocr_engine import OCREngine

ocr = OCREngine()

text = ocr.extract_text("Vinit adharCard.jpg")

print("\nExtracted Text:\n")
print(text)