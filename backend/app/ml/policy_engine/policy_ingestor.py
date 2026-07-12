# backend/app/ml/policy_engine/policy_ingestor.py
import re
from typing import Dict, Any

class PolicyIngestor:
    """
    Processes a raw text extract from a newly uploaded PDF policy document
    and uses heuristic rules to automatically extract scheme constraints.
    Avoids heavy transformers in favor of fast RegExp pattern matching for efficiency.
    """

    @staticmethod
    def extract_constraints(text: str) -> Dict[str, Any]:
        """
        Parses text to find common agricultural policy constraints like:
        - Minimum land (e.g., "minimum 1.5 hectares")
        - Age requirement (e.g., "age above 18 years" or "between 18 and 60")
        - Required crops
        """
        constraints = {
            "min_land_hectares": None,
            "max_land_hectares": None,
            "min_age": None,
            "max_age": None,
            "required_crops": []
        }

        # 1. Land constraint extraction
        # Matches "minimum X hectares" or "at least X ha"
        min_land_match = re.search(r'(?:minimum|at least|>)\s*(\d+(?:\.\d+)?)\s*(?:hectares|hectare|ha|acres)', text, re.IGNORECASE)
        if min_land_match:
            constraints["min_land_hectares"] = float(min_land_match.group(1))
            
        # Matches "maximum X hectares" or "up to X ha"
        max_land_match = re.search(r'(?:maximum|up to|<)\s*(\d+(?:\.\d+)?)\s*(?:hectares|hectare|ha|acres)', text, re.IGNORECASE)
        if max_land_match:
            constraints["max_land_hectares"] = float(max_land_match.group(1))

        # 2. Age constraint extraction
        # Matches "age above 18" or "above 18 years"
        age_above_match = re.search(r'(?:age above|above|older than|>)\s*(\d{2})\s*(?:years?)?', text, re.IGNORECASE)
        if age_above_match:
            constraints["min_age"] = int(age_above_match.group(1))
            
        # Matches "between 18 and 60"
        age_between_match = re.search(r'between\s*(\d{2})\s*and\s*(\d{2})', text, re.IGNORECASE)
        if age_between_match:
            constraints["min_age"] = int(age_between_match.group(1))
            constraints["max_age"] = int(age_between_match.group(2))

        # 3. Crop Keyword extraction (very basic heuristic)
        common_crops = ["wheat", "rice", "cotton", "sugarcane", "maize", "soybean", "onion"]
        for crop in common_crops:
            if re.search(rf'\b{crop}\b', text, re.IGNORECASE):
                constraints["required_crops"].append(crop.capitalize())

        return constraints

    @staticmethod
    def process_new_document(document_text: str, scheme_name: str) -> dict:
        """
        Endpoint function intended to be run as a FastAPI BackgroundTask.
        It parses the text and ideally saves the constraints to the database.
        """
        print(f"🔄 Policy Ingestor: Parsing new document for '{scheme_name}'...")
        constraints = PolicyIngestor.extract_constraints(document_text)
        print(f"✅ Policy Ingestor: Extracted constraints: {constraints}")
        
        # In a full flow, you would inject the `db` here and update the scheme collection
        # e.g., db.schemes.update_one({"name": scheme_name}, {"$set": {"ml_constraints": constraints}})
        
        return {
            "scheme_name": scheme_name,
            "automated_constraints": constraints,
            "status": "processed"
        }
