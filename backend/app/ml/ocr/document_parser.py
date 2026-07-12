import re


class DocumentParser:

    def extract_aadhar(self, text: str):
        # Remove common Aadhaar noise but keep digits
        # Traditional Aadhaar is 4-4-4 digits
        # Let's look for exactly 12 digits that might be separated by spaces or hyphens
        
        # 1. Clean the text but keep digits and spaces/hyphens
        cleaned = re.sub(r"[^\d\s-]", " ", text)
        
        # 2. Match 12 digits with optional multiple spaces or hyphens between 4-digit blocks
        # Pattern: 4 digits, then spaces/hyphens, then 4 digits, then spaces/hyphens, then 4 digits
        match = re.search(r"(\d{4})[\s-]*(\d{4})[\s-]*(\d{4})", cleaned)
        if match:
            return "".join(match.groups())
            
        # 3. Fallback: Just look for any consecutive 12 digits
        match_simple = re.search(r"\d{12}", cleaned.replace(" ", ""))
        return match_simple.group() if match_simple else None


    def extract_pan(self, text: str):
        # PAN Pattern: 5 letters, 4 digits, 1 letter
        match = re.search(r"([A-Z]{5}[0-9]{4}[A-Z])", text.upper())
        return match.group(1) if match else None