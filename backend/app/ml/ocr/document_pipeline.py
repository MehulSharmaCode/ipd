from app.ml.ocr.ocr_engine_v2 import OCREngineV2


class DocumentPipeline:

    def __init__(self):

        self.ocr = OCREngineV2()

    def process_document(self, file_path: str, expected_type: str):
        """
        Process the document and verify its authenticity.
        """
        verification_result = self.ocr.verify_document(file_path, expected_type)
        
        # Adapt V2 result to the pipeline's expected format
        return {
            "is_verified": verification_result.get("is_valid", False),
            "extracted_id": verification_result.get("extracted_id"),
            "aadhar": verification_result.get("extracted_id") if verification_result.get("doc_type") == "aadhar" else None,
            "pan": verification_result.get("extracted_id") if verification_result.get("doc_type") == "pan" else None,
            "raw_text": verification_result.get("raw_text_snippet"),
            "error": verification_result.get("error")
        }