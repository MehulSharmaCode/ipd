"""
LLM & Heuristic Scheme Rule Extractor
---------------------------------------
Extracts structured eligibility rules and benefit calculations from
free-text scheme descriptions fetched from myScheme.gov.in.

Primary: Google Gemini API (if GEMINI_API_KEY is configured).
Fallback: Heuristic NLP pattern extractor for land_size, income, farmer_type,
          crop, and financial benefit amounts.

Output Schema matches RulesEngine:
    rules: [{field, operator, value}, ...]
    benefit_calculation: {type, base_rate/base_rate_per_ha, crop_multiplier_enabled}
"""

import html
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Lazy import for Gemini
_genai = None
_model = None


def _get_gemini_model():
    """Lazy-init the Gemini model on first use if API key is provided."""
    global _genai, _model
    if _model is not None:
        return _model
    try:
        import os
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _genai = genai
        _model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Gemini model initialized for rule extraction")
        return _model
    except Exception as e:
        logger.warning(f"Could not initialize Gemini model: {e}")
        return None


# Few-shot examples matching the YAML schema
_FEW_SHOT_EXAMPLES = """
Example 1 — PM Kisan Samman Nidhi:
Input eligibility text: "Small and Marginal Farmers with cultivable land up to 2 hectares. Family income should not exceed ₹2,00,000 per annum."
Output:
{
  "rules": [
    {"field": "farmer_type", "operator": "in", "value": ["small", "medium"]},
    {"field": "land_size", "operator": "<=", "value": 2},
    {"field": "income", "operator": "<=", "value": 200000}
  ],
  "benefit_calculation": {"type": "flat_rate", "base_rate": 6000}
}

Example 2 — Drip Irrigation Subsidy:
Input eligibility text: "Farmers having more than 1 hectare of irrigable land. Small and medium category farmers are eligible. Subsidy of ₹40,000 per hectare for drip/sprinkler systems."
Output:
{
  "rules": [
    {"field": "land_size", "operator": ">", "value": 1},
    {"field": "farmer_type", "operator": "in", "value": ["small", "medium"]}
  ],
  "benefit_calculation": {"type": "per_hectare_subsidy", "base_rate_per_ha": 40000, "crop_multiplier_enabled": false}
}
"""

_SYSTEM_PROMPT = """You are a structured data extraction assistant for Indian government schemes.

Given a scheme's title, eligibility description, and benefits text, extract ALL eligibility criteria present in the text into structured rules.

1. **rules**: A JSON list of eligibility conditions. Each rule must have:
   - "field": A snake_case field descriptor (e.g. occupation_type, education_level, age, category, gender, is_differently_abled, state, income, land_size, crop, farmer_type, employment_status, business_type, marital_status, etc.).
   - "operator": One of: ==, !=, <, <=, >, >=, in, not_in
   - "value": The threshold value (string, number, boolean, or list of strings).

   Common Field Examples:
   - occupation_type: "farmer", "business_owner", "weaver", "construction_worker", "faculty_member", "student", "doctor", "artisan", "fisherman", "corporate", etc.
   - education_level: "phd", "post_graduate", "graduate", "diploma", "iti", "class_6_12", etc.
   - age: integer min/max age
   - category: "sc", "st", "obc", "general"
   - gender: "female", "male"
   - is_differently_abled: true/false
   - state: State/UT name (e.g. "Maharashtra", "Uttar Pradesh", "Mizoram", "Andaman and Nicobar Islands")
   - income: Max annual income limit in INR
   - land_size: Max/min land size in hectares
   - crop: list of eligible crops (e.g. ["wheat", "rice"])
   - farmer_type: ["small", "medium"] or "large"

CRITICAL DISAMBIGUATION RULE: If a scheme mentions a crop/commodity (e.g. cotton, sugarcane, rice, pulses, tea) but targets a processing, ginning, milling, manufacturing, or commercial business entity (e.g. ginning mill, textile unit, sugar mill, rice mill, processing plant, industrial unit, commercial enterprise, traders) rather than an individual cultivator/farmer, extract 'occupation_type': 'business_owner'. Do NOT classify processing/manufacturing business entities as individual farmers.

If the scheme genuinely contains NO eligibility requirements or restrictions whatsoever, return "rules": [].

2. **benefit_calculation**:
   - "type": Either "flat_rate" or "per_hectare_subsidy"
   - "base_rate": Amount in INR (integer)
   - "base_rate_per_ha": Amount per hectare in INR (integer)

Return ONLY valid JSON.
"""


def _is_constraining_rule(rule: Dict[str, Any]) -> bool:
    """
    Validates whether a rule is genuinely constraining (discriminating) or a non-constraining catch-all.
    Rejects generic rules that match 100% of candidates.
    """
    field = rule.get("field")
    op = rule.get("operator")
    val = rule.get("value")

    if field == "farmer_type":
        if isinstance(val, list) and set(val) >= {"small", "medium", "large"}:
            return False

    if field == "state":
        if isinstance(val, list) and len(val) > 34:
            return False
        if isinstance(val, str) and val.lower() in ["all states", "pan-india", "national", "india", "all", "all state"]:
            return False

    if field == "land_size" and op in ["<=", "<"] and isinstance(val, (int, float)) and val >= 999:
        return False

    if field == "income" and op in ["<=", "<"] and isinstance(val, (int, float)) and val >= 100000000:
        return False

    if field == "crop":
        if isinstance(val, list) and len(val) > 15:
            return False
        if isinstance(val, str) and val.lower() in ["all crops", "any crop", "all"]:
            return False

    if field == "category":
        if isinstance(val, list) and set(val) >= {"sc", "st", "obc", "general"}:
            return False
        if isinstance(val, str) and val.lower() in ["all categories", "all", "any"]:
            return False

    if field == "gender":
        if isinstance(val, list) and set(val) >= {"male", "female", "other"}:
            return False
        if isinstance(val, str) and val.lower() in ["all genders", "all", "any", "both"]:
            return False

    if field == "age":
        if op in ["<=", "<"] and isinstance(val, (int, float)) and val >= 120:
            return False
        if op in [">=", ">"] and isinstance(val, (int, float)) and val <= 0:
            return False

    return True


def _heuristic_extract_rules(text: str, benefits_text: str = "", scheme_name: str = "") -> Dict[str, Any]:
    """
    Regex & NLP heuristic pattern extractor for eligibility constraints and benefit amounts.
    Extracts age, category, gender, disability, state, land size, income, occupation, education, farmer types, and crops.
    """
    raw_combined = f"{scheme_name} {text} {benefits_text}".strip()
    combined_text = html.unescape(raw_combined).lower()
    if not combined_text or len(combined_text) < 5:
        return {
            "rules": [],
            "benefit_calculation": {"type": "flat_rate", "base_rate": 0},
            "extraction_method": "heuristic",
            "extraction_confidence": "low"
        }

    rules = []
    eligibility_lower = text.lower()
    
    # 1. Occupation Type Extraction
    if any(kw in eligibility_lower for kw in ["ginning", "processing unit", "processing plant", "textile policy", "textile unit", "textile mill", "sugar mill", "rice mill", "oil mill", "flour mill", "cold storage unit", "food processing", "industrial unit", "manufacturing unit", "enterprise", "traders", "commercial unit", "handicraft artisans", "tirtha yatra", "road construction", "orunodoi"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "business_owner"})
    elif any(kw in eligibility_lower for kw in ["weaver", "charkha", "sericulture reeler", "powerloom", "textile worker", "loom"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "weaver"})
    elif any(kw in eligibility_lower for kw in ["construction worker", "bocwwb", "unregistered worker"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "construction_worker"})
    elif any(kw in eligibility_lower for kw in ["faculty member", "professor", "academician", "researcher", "scientist", "science chair", "teacher"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "faculty_member"})
    elif any(kw in eligibility_lower for kw in ["student", "internship", "pursuing degree", "diploma holder", "ph.d."]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "student"})
    elif any(kw in eligibility_lower for kw in ["journalism", "journalist", "media", "reporter", "newspaper", "magazine", "broadcasting"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "media_professional"})
    elif any(kw in eligibility_lower for kw in ["artisan", "craftsman", "weaver", "handicraft", "handloom"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "artisan"})
    elif any(kw in eligibility_lower for kw in ["entrepreneur", "startup", "founder"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "entrepreneur"})
    elif any(kw in eligibility_lower for kw in ["civil servant", "government employee", "police", "armed forces", "defence personnel"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "government_employee"})
    elif any(kw in eligibility_lower for kw in ["nurse", "pharmacist", "paramedic"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "medical_professional"})
    elif any(kw in eligibility_lower for kw in ["lawyer", "advocate", "legal professional"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "legal_professional"})
    elif any(kw in eligibility_lower for kw in ["driver", "mechanic", "transport worker"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "transport_worker"})
    elif any(kw in eligibility_lower for kw in ["industrial park", "companies act", "spv", "pli scheme", "specialty steel", "petrochemicals"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "corporate"})
    elif any(kw in eligibility_lower for kw in ["medical practitioner", "electro-medical", "doctor"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "doctor"})
    elif any(kw in eligibility_lower for kw in ["fisherman", "fisheries cooperative", "fishermen"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "fisherman"})
    elif any(kw in eligibility_lower for kw in ["farmer", "agriculturist", "cultivator", "kisan"]):
        rules.append({"field": "occupation_type", "operator": "==", "value": "farmer"})

    # 2. Education Level Extraction
    if re.search(r'\b(ph\.?d|doctoral)\b', combined_text):
        rules.append({"field": "education_level", "operator": "==", "value": "phd"})
    elif re.search(r'\b(post[- ]graduate|master|\bm\.?tech|\bm\.?e\.?)\b', combined_text):
        rules.append({"field": "education_level", "operator": "==", "value": "post_graduate"})
    elif re.search(r'\b(bachelor|graduation|\bb\.?tech|\bb\.?e\.?)\b', combined_text):
        rules.append({"field": "education_level", "operator": "==", "value": "graduate"})
    elif re.search(r'\b(diploma|iti)\b', combined_text):
        rules.append({"field": "education_level", "operator": "==", "value": "diploma"})
    elif re.search(r'\b(classes? 6 (?:to|12)|class 9|class 10|matric|higher secondary)\b', combined_text):
        rules.append({"field": "education_level", "operator": "==", "value": "class_6_12"})

    # 3. Land Size Extraction (Extract BOTH min and max if present, handling optional 'of')
    max_land = re.search(r'(?:up to|maximum|less than|<=|<|not exceeding)(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*(?:hectares|hectare|ha|acres)', combined_text)
    if max_land:
        val = float(max_land.group(1))
        if "acre" in max_land.group(0):
            val = round(val * 0.4047, 2)
        rules.append({"field": "land_size", "operator": "<=", "value": val})

    min_land = re.search(r'(?:at least|minimum|more than|above|>)(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*(?:hectares|hectare|ha|acres)', combined_text)
    if min_land:
        val = float(min_land.group(1))
        if "acre" in min_land.group(0):
            val = round(val * 0.4047, 2)
        rules.append({"field": "land_size", "operator": ">=", "value": val})

    # 4. Income Limit Extraction (supports 'exceed', 'under', 'below', 'not exceeding', etc.)
    income_match = re.search(r'(?:income|earning)(?:[^\d]*?)(?:below|up to|less than|<=|<|not exceeding|under|exceed|exceeding)\s*(?:more than)?\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(lakh|lakhs|k|thousand)?', combined_text)
    if income_match:
        raw_num = float(income_match.group(1).replace(",", ""))
        unit = (income_match.group(2) or "").lower()
        if "lakh" in unit:
            raw_num *= 100000
        elif unit == "k" or "thousand" in unit:
            raw_num *= 1000
        rules.append({"field": "income", "operator": "<=", "value": int(raw_num)})

    # 5. Age Limit Extraction
    # First, handle explicit range phrasing
    age_range = re.search(r'(?:age|aged|child|children|applicant|person|youth)?\s*(?:should be|must be|is)?\s*between\s*(\d{1,2})\s*(?:to|-|and)\s*(\d{1,2})\s*(?:years|yrs)?', combined_text)
    if age_range:
        rules.append({"field": "age", "operator": ">=", "value": int(age_range.group(1))})
        rules.append({"field": "age", "operator": "<=", "value": int(age_range.group(2))})
    
    # Check for "18 to 50 years age group"
    age_group = re.search(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*(?:years|yrs)\s*(?:age)?\s*group', combined_text)
    if age_group and not age_range:
        rules.append({"field": "age", "operator": ">=", "value": int(age_group.group(1))})
        rules.append({"field": "age", "operator": "<=", "value": int(age_group.group(2))})

    # Check for Max Age
    # e.g. "not be greater than 50 years", "below 30 years of age", "age should be below 30", "not more than 65 years"
    max_age_match = re.search(r'(?:(?:age|aged)\s*(?:below|under|up to|less than|<=|<|not exceeding|not be greater than)\s*(\d{1,2})\s*(?:years|yrs)?)|(?:below\s*(\d{1,2})\s*(?:years|yrs)\s*(?:of age)?)|(?:not\s*(?:exceed|be greater than|be more than|more than)\s*(\d{1,2})\s*(?:years|yrs))', combined_text)
    if max_age_match:
        val = max_age_match.group(1) or max_age_match.group(2) or max_age_match.group(3)
        if val:
            rules.append({"field": "age", "operator": "<=", "value": int(val)})

    # Check for Min Age (Make sure not preceded by "not")
    # e.g. "at least 18 years", "above 18 years of age", "60 years or above", "18 years of age or above", "attained the age of 60 years and above"
    min_age_match = re.search(r'(?<!not\s)(?<!not be\s)(?:(?:age|aged)\s*(?:above|at least|minimum|over|>=|>)\s*(\d{1,2})\s*(?:years|yrs)?)|(?:(?:at least|minimum|above|more than)\s*(\d{1,2})\s*(?:years|yrs))|(?:(\d{1,2})\s*(?:years|yrs)(?:\s*of age)?\s*(?:or above|and above))', combined_text)
    if min_age_match:
        val = min_age_match.group(1) or min_age_match.group(2) or min_age_match.group(3)
        # Avoid matching if max_age_match caught the exact same number (e.g. "not more than 65" caught by max, but min might catch "more than 65")
        if not (max_age_match and int(val) == int(max_age_match.group(1) or max_age_match.group(2) or max_age_match.group(3))):
            rules.append({"field": "age", "operator": ">=", "value": int(val)})

    # 6. Gender Extraction
    if any(kw in combined_text for kw in ["woman", "women", "female", "girl", "lady", "ladies", "housewives", "widow"]):
        rules.append({"field": "gender", "operator": "==", "value": "female"})

    # 7. Disability / Differently Abled Extraction
    if any(kw in combined_text for kw in ["differently abled", "disabled", "disability", "handicapped", "divyang", "pwd", "pwds", "persons with disabilities", "surgical grant", "rehabilitation of pwd", "cerebral palsy", "intellectually impaired", "mentally deficient", "orphan", "hearing impairment", "visual impairment", "speech impairment", "deaf", "blind"]):
        rules.append({"field": "is_differently_abled", "operator": "==", "value": True})

    # 8. Category Extraction
    if re.search(r'\b(scheduled caste|sc)\b', combined_text):
        rules.append({"field": "category", "operator": "==", "value": "SC"})
    elif re.search(r'\b(scheduled tribe|st)\b', combined_text):
        rules.append({"field": "category", "operator": "==", "value": "ST"})
    elif re.search(r'\b(other backward class|obc)\b', combined_text):
        rules.append({"field": "category", "operator": "==", "value": "OBC"})

    # 9. Farmer Type Extraction (Only specific constraints)
    if any(kw in combined_text for kw in ["small and marginal", "small farmer", "marginal farmer", "small & marginal"]):
        rules.append({"field": "farmer_type", "operator": "in", "value": ["small", "medium"]})
    elif "large farmer" in combined_text:
        rules.append({"field": "farmer_type", "operator": "==", "value": "large"})

    # 10. State Constraint Extraction (Full All-India State/UT List & Regions)
    indian_states = [
        "maharashtra", "uttar pradesh", "rajasthan", "gujarat", "punjab", "haryana",
        "madhya pradesh", "karnataka", "tamil nadu", "andhra pradesh", "telangana",
        "kerala", "bihar", "west bengal", "odisha", "assam", "jharkhand", "chhattisgarh",
        "uttarakhand", "himachal pradesh", "mizoram", "meghalaya", "puducherry", "goa",
        "jammu & kashmir", "jammu and kashmir", "delhi", "tripura", "manipur", "nagaland",
        "sikkim", "arunachal pradesh", "ladakh", "andaman & nicobar", "andaman and nicobar",
        "chandigarh", "dadra and nagar haveli", "daman and diu", "lakshadweep"
    ]
    
    region_mapping = {
        "north eastern region": ["Arunachal Pradesh", "Assam", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"],
        "ner": ["Arunachal Pradesh", "Assam", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"],
        "traditional areas": ["Kerala", "Tamil Nadu", "Karnataka"],
        "seed spice growing states": ["Rajasthan", "Gujarat", "Madhya Pradesh", "Andhra Pradesh", "Telangana"],
        "spice growing states": ["Kerala", "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Gujarat", "Rajasthan", "Madhya Pradesh", "Assam", "Meghalaya", "Sikkim", "West Bengal", "Arunachal Pradesh", "Nagaland", "Manipur", "Mizoram", "Tripura"],
        "spice-growing states": ["Kerala", "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Gujarat", "Rajasthan", "Madhya Pradesh", "Assam", "Meghalaya", "Sikkim", "West Bengal", "Arunachal Pradesh", "Nagaland", "Manipur", "Mizoram", "Tripura"],
        "pepper growing states": ["Kerala", "Karnataka", "Tamil Nadu"],
        "turmeric growing states": ["Andhra Pradesh", "Telangana", "Tamil Nadu", "Odisha", "West Bengal", "Maharashtra", "Karnataka", "Gujarat", "Assam"],
        "non-traditional areas": ["Andhra Pradesh", "Odisha", "Maharashtra", "Madhya Pradesh", "Chhattisgarh", "Gujarat", "Andaman and Nicobar Islands"], # Common broad term, but we should rely on explicit names or specific known mappings
    }
    
    matched_states = set()
    
    # Check explicit states
    for state_name in indian_states:
        if re.search(rf'\b{state_name}\b', combined_text):
            clean_state = "Jammu and Kashmir" if "jammu" in state_name else ("Andaman and Nicobar Islands" if "andaman" in state_name else state_name.title())
            matched_states.add(clean_state)
            
    # Check region keywords
    for region, states in region_mapping.items():
        if re.search(rf'\b{region}\b', combined_text):
            for s in states:
                matched_states.add(s)
                
    if matched_states:
        matched_states = sorted(list(matched_states))
        if len(matched_states) == 1:
            rules.append({"field": "state", "operator": "==", "value": matched_states[0]})
        else:
            rules.append({"field": "state", "operator": "in", "value": matched_states})

    # 11. Crop Keyword Extraction
    common_crops = ["wheat", "rice", "cotton", "sugarcane", "maize", "soybean", "mustard", "pulses", "onion", "groundnut"]
    found_crops = [crop for crop in common_crops if re.search(rf'\b{crop}\b', combined_text)]
    if found_crops:
        rules.append({"field": "crop", "operator": "in", "value": found_crops})

    # Filter rules to ensure every rule is genuinely constraining
    constrained_rules = [r for r in rules if _is_constraining_rule(r)]

    # Financial Benefit Calculation Extraction
    benefit_calc = {"type": "flat_rate", "base_rate": 0}
    per_ha_match = re.search(r'(?:subsidy|financial assistance|grant|benefit)\s*(?:of|up to)?\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*)\s*(?:per|/)\s*(?:hectare|ha)', combined_text)
    if per_ha_match:
        amount = int(per_ha_match.group(1).replace(",", ""))
        benefit_calc = {
            "type": "per_hectare_subsidy",
            "base_rate_per_ha": amount,
            "crop_multiplier_enabled": False
        }
    else:
        flat_match = re.search(r'(?:financial assistance|subsidy|incentive|grant|amount|benefit)\s*(?:of|up to)?\s*(?:rs\.?|₹)\s*(\d+(?:,\d+)*)', combined_text)
        if flat_match:
            amount = int(flat_match.group(1).replace(",", ""))
            if amount > 100:
                benefit_calc = {
                    "type": "flat_rate",
                    "base_rate": amount
                }

    return {
        "rules": constrained_rules,
        "benefit_calculation": benefit_calc,
        "extraction_method": "heuristic",
        "extraction_confidence": "high" if len(constrained_rules) > 1 else ("medium" if constrained_rules else "low")
    }


def _parse_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse LLM JSON output cleanly with open-ended field support."""
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict) or "rules" not in parsed:
            return None

        valid_operators = {"==", "!=", "<", "<=", ">", ">=", "in", "not_in"}
        validated_rules = []
        for rule in parsed.get("rules", []):
            if (isinstance(rule, dict) and
                isinstance(rule.get("field"), str) and
                len(rule.get("field", "").strip()) > 0 and
                rule.get("operator") in valid_operators and
                "value" in rule and
                _is_constraining_rule(rule)):
                # Clean field name to lowercase snake_case
                rule["field"] = rule["field"].strip().lower().replace(" ", "_")
                validated_rules.append(rule)

        parsed["rules"] = validated_rules
        bc = parsed.get("benefit_calculation", {})
        if not isinstance(bc, dict) or "type" not in bc:
            parsed["benefit_calculation"] = {"type": "flat_rate", "base_rate": 0}

        return parsed
    except Exception as e:
        logger.warning(f"Could not parse LLM JSON: {e}")
        return None


async def extract_rules_from_text(
    scheme_name: str,
    eligibility_text: str,
    benefits_text: str = "",
) -> Dict[str, Any]:
    """
    Extract structured rules and benefit_calculation.
    Uses Gemini LLM if API key is present; otherwise falls back to heuristic parser.
    """
    model = _get_gemini_model()

    # If Gemini model is available, attempt LLM extraction
    if model is not None:
        try:
            user_prompt = f"Scheme Name: {scheme_name}\nEligibility: {eligibility_text}\nBenefits: {benefits_text}"
            response = model.generate_content(
                _SYSTEM_PROMPT + user_prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 1024}
            )
            if response and response.text:
                parsed = _parse_llm_response(response.text)
                if parsed and parsed.get("rules"):
                    return {
                        "rules": parsed["rules"],
                        "benefit_calculation": parsed.get("benefit_calculation", {"type": "flat_rate", "base_rate": 0}),
                        "extraction_method": "llm",
                        "extraction_confidence": "high"
                    }
        except Exception as e:
            logger.warning(f"Gemini LLM extraction failed for '{scheme_name}': {e}")

    # Fallback to heuristic pattern extractor
    return _heuristic_extract_rules(eligibility_text, benefits_text, scheme_name=scheme_name)
