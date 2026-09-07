# backend/app/document_processing/normalizer.py
"""
Semantic Normalization Layer
============================
Responsibility: Transform raw extracted field values (from OCR or Vision processors)
into canonical frontend/database enum values.

Matches supported in Version 1:
  1. Exact match          (multiplier 1.00)
  2. Case-insensitive     (multiplier 1.00)
  3. Contains match       (multiplier 0.95, enum fields only)
  4. Devanagari/Marathi   (multiplier 0.90)

Unmatched values are left unchanged. No fuzzy matching or hallucination.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any
from app.document_processing.schemas import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Synonym & Enum Definitions
# Structure: CanonicalValue -> { "synonyms": [latin_strings], "devanagari": [devanagari_strings] }
# ----------------------------------------------------------------------

GENDER_SPEC: Dict[str, Dict[str, List[str]]] = {
    "Male": {
        "synonyms": ["male", "m"],
        "devanagari": ["पुरुष"],
    },
    "Female": {
        "synonyms": ["female", "f"],
        "devanagari": ["महिला", "स्त्री"],
    },
    "Other": {
        "synonyms": ["transgender", "t", "other"],
        "devanagari": ["तृतीयपंथी"],
    },
}

IRRIGATION_SPEC: Dict[str, Dict[str, List[str]]] = {
    "Well": {
        "synonyms": ["well", "well irrigation", "open well", "tube well", "tubewell"],
        "devanagari": ["विहीर"],
    },
    "Canal": {
        "synonyms": ["canal", "canal irrigation"],
        "devanagari": ["कालवा"],
    },
    "Rain": {
        "synonyms": ["rain", "rainfed", "rain-fed", "rainfed agriculture", "rain-fed agriculture"],
        "devanagari": ["जिरायत", "कोरडवाहू"],
    },
    "River": {
        "synonyms": ["river", "river irrigation"],
        "devanagari": ["नदी"],
    },
    "Borewell": {
        "synonyms": ["borewell", "bore well", "boarwell"],
        "devanagari": ["बोअरवेल"],
    },
}

SOIL_TYPE_SPEC: Dict[str, Dict[str, List[str]]] = {
    "Alluvial": {
        "synonyms": ["alluvial", "alluvial soil"],
        "devanagari": ["गाळाची माती", "गाळाची"],
    },
    "Black": {
        "synonyms": ["black", "black cotton", "black cotton soil", "black soil", "regur"],
        "devanagari": ["काळी माती", "काळी कापूस माती", "काळी"],
    },
    "Red": {
        "synonyms": ["red", "red soil", "red laterite"],
        "devanagari": ["तांबडी माती", "लाल माती", "लाल", "तांबडी"],
    },
    "Laterite": {
        "synonyms": ["laterite", "laterite soil", "jambhi"],
        "devanagari": ["जांभी माती", "जांभी"],
    },
    "Desert": {
        "synonyms": ["desert", "desert soil", "sandy", "sandy soil"],
        "devanagari": ["वाळवंटी माती", "वाळवंटी"],
    },
    "Mountain": {
        "synonyms": ["mountain", "mountain soil", "hill soil"],
        "devanagari": ["डोंगरी माती", "डोंगरी"],
    },
}

OWNERSHIP_SPEC: Dict[str, Dict[str, List[str]]] = {
    "Owned": {
        "synonyms": ["owned", "individual", "self", "personal"],
        "devanagari": ["स्वतःची", "खुद"],
    },
    "Leased": {
        "synonyms": ["leased", "lease", "rent"],
        "devanagari": ["भाडेपट्टी"],
    },
    "Shared": {
        "synonyms": ["shared", "joint", "co-owned", "coowned", "inherited"],
        "devanagari": ["संयुक्त"],
    },
}

SEASON_SPEC: Dict[str, Dict[str, List[str]]] = {
    "Kharif": {
        "synonyms": ["kharif", "kharip", "monsoon", "rainy season"],
        "devanagari": ["खरीप", "खरीफ", "खरिफ"],
    },
    "Rabi": {
        "synonyms": ["rabi", "rabbi", "winter crop", "winter season"],
        "devanagari": ["रबी", "रब्बी"],
    },
    "Zaid": {
        "synonyms": ["zaid", "zayad", "summer crop", "summer season"],
        "devanagari": ["जायद", "उन्हाळी"],
    },
}

# Field name alias map to canonical spec
FIELD_SPECS: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "gender": GENDER_SPEC,
    "irrigation": IRRIGATION_SPEC,
    "irrigation_type": IRRIGATION_SPEC,
    "soil_type": SOIL_TYPE_SPEC,
    "ownership_type": OWNERSHIP_SPEC,
    "land_ownership": OWNERSHIP_SPEC,
    "season": SEASON_SPEC,
    "crop_season": SEASON_SPEC,
}

CONFIDENCE_MULTIPLIERS = {
    "EXACT": 1.00,
    "CASE_INSENSITIVE": 1.00,
    "CONTAINS": 0.95,
    "DEVANAGARI": 0.90,
}


class SemanticNormalizer:
    """
    Normalizes extracted fields in an ExtractionResult to canonical enum values.
    Operates on a strict deterministic matching pipeline:
      1. Exact match
      2. Case-insensitive match
      3. Contains match
      4. Devanagari match
    """

    def normalize(self, result: ExtractionResult) -> ExtractionResult:
        """
        Normalize enum fields in-place on the ExtractionResult.
        """
        if not result.success or not result.fields:
            return result

        for field_name, field_obj in list(result.fields.items()):
            if field_name not in FIELD_SPECS:
                continue

            raw_val = field_obj.value
            if not isinstance(raw_val, str) or not raw_val.strip():
                continue

            clean_val = raw_val.strip()
            spec = FIELD_SPECS[field_name]

            normalized_val, match_type = self._resolve_canonical(clean_val, spec)
            if normalized_val is not None and match_type is not None:
                multiplier = CONFIDENCE_MULTIPLIERS[match_type]
                old_conf = field_obj.confidence
                new_conf = min(old_conf, old_conf * multiplier)

                field_obj.value = normalized_val
                field_obj.confidence = new_conf

                logger.info(
                    "AUDIT NORMALIZATION | doc='%s' | field='%s' | raw='%s' -> normalized='%s' | match='%s' | conf=%.3f -> %.3f",
                    result.document_type,
                    field_name,
                    clean_val,
                    normalized_val,
                    match_type,
                    old_conf,
                    new_conf,
                )

        return result

    def _resolve_canonical(
        self, raw: str, spec: Dict[str, Dict[str, List[str]]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Deterministic matching pipeline:
          1. Exact match
          2. Case-insensitive match
          3. Contains match
          4. Devanagari match
        Returns (canonical_value, match_type) or (None, None).
        """
        raw_lower = raw.lower()

        # Step 1: Exact match against canonical key
        for canonical_key in spec.keys():
            if raw == canonical_key:
                return canonical_key, "EXACT"

        # Step 2: Case-insensitive match against canonical key or latin synonyms
        for canonical_key, data in spec.items():
            if raw_lower == canonical_key.lower():
                return canonical_key, "CASE_INSENSITIVE"
            for syn in data.get("synonyms", []):
                if raw_lower == syn.lower():
                    return canonical_key, "CASE_INSENSITIVE"

        # Step 3: Contains match (check if raw contains synonym or synonym contains raw)
        for canonical_key, data in spec.items():
            if canonical_key.lower() in raw_lower:
                return canonical_key, "CONTAINS"
            for syn in data.get("synonyms", []):
                syn_lower = syn.lower()
                if syn_lower in raw_lower or raw_lower in syn_lower:
                    return canonical_key, "CONTAINS"

        # Step 4: Devanagari synonym match (exact/contains on Devanagari strings)
        for canonical_key, data in spec.items():
            for dev_syn in data.get("devanagari", []):
                if dev_syn in raw:
                    return canonical_key, "DEVANAGARI"

        return None, None

    # ------------------------------------------------------------------
    # Business Rule Validation
    # ------------------------------------------------------------------

    # Valid canonical values for each enum field (after normalization)
    _VALID_ENUMS: Dict[str, set] = {
        "gender":         {"Male", "Female", "Other"},
        "irrigation":     {"Well", "Canal", "Rain", "River", "Borewell"},
        "irrigation_type":{"Well", "Canal", "Rain", "River", "Borewell"},
        "soil_type":      {"Alluvial", "Black", "Red", "Laterite", "Desert", "Mountain"},
        "ownership_type": {"Owned", "Leased", "Shared"},
        "land_ownership": {"Owned", "Leased", "Shared"},
        "season":         {"Kharif", "Rabi", "Zaid"},
        "crop_season":    {"Kharif", "Rabi", "Zaid"},
    }

    def validate_business_rules(self, result: ExtractionResult) -> ExtractionResult:
        """
        Validate extracted field values against simple business rules.
        Removes impossible values and adds warnings.
        Runs AFTER normalization, BEFORE ProfileBuilder.
        """
        if not result.success or not result.fields:
            return result

        warnings = list(result.validation.get("warnings", []))
        fields_to_remove: list[str] = []

        for field_name, field_obj in result.fields.items():
            if field_obj.value is None:
                continue

            # ── Enum validation: after normalization, value MUST be canonical ──
            if field_name in self._VALID_ENUMS:
                if field_obj.value not in self._VALID_ENUMS[field_name]:
                    logger.warning(
                        "BUSINESS RULE VIOLATION | doc='%s' | field='%s' | value='%s' not in valid set %s — removing",
                        result.document_type, field_name, field_obj.value,
                        self._VALID_ENUMS[field_name],
                    )
                    warnings.append(
                        f"'{field_name}' value '{field_obj.value}' is not a recognized option. "
                        f"Please select manually."
                    )
                    fields_to_remove.append(field_name)
                    continue

            # ── Land area validation ──────────────────────────────────────
            if field_name == "land_area":
                validated = self._validate_land_area(field_obj.value, result.document_type)
                if validated is None:
                    warnings.append(
                        f"Land area value '{field_obj.value}' could not be validated. "
                        f"Please enter manually."
                    )
                    fields_to_remove.append(field_name)
                else:
                    field_obj.value = validated

            # ── Survey number validation ─────────────────────────────────
            if field_name == "survey_number":
                val_str = str(field_obj.value).strip()
                # Remove Devanagari numerals for checking
                latin = val_str.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
                # Must be numeric or alphanumeric, max 10 chars
                if len(latin) > 20 or not re.match(r'^[\w/\-]+$', latin):
                    warnings.append(
                        f"Survey number '{field_obj.value}' appears invalid."
                    )
                    fields_to_remove.append(field_name)

        # Remove invalid fields
        for fn in fields_to_remove:
            del result.fields[fn]

        result.validation["warnings"] = warnings
        if warnings and not result.validation.get("warnings_original"):
            result.validation["valid"] = result.validation.get("valid", True)

        return result

    def _validate_land_area(self, raw_value: Any, doc_type: str) -> Optional[str]:
        """
        Parse and validate land area values.
        Returns the validated string or None if invalid.

        Acceptable formats:
          - "6 हेक्टर 11 आर" → "6.11"
          - "2.5 hectare" → "2.5"
          - "6.11" → "6.11"
          - "611" → None (likely an error — 611 hectares is implausible for a single farmer)
        """
        if not isinstance(raw_value, str):
            raw_value = str(raw_value)

        val = raw_value.strip()

        # Translate Devanagari digits to Latin
        val_latin = val.translate(str.maketrans("०१२३४५६७८९", "0123456789"))

        # Pattern 1: "X हेक्टर Y आर" or "X hectare Y are"
        hect_are = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:हेक्टर|hectare|hect)[\s,]*(\d+(?:\.\d+)?)\s*(?:आर|are|ar)?',
            val_latin, re.IGNORECASE
        )
        if hect_are:
            hectares = float(hect_are.group(1))
            ares = float(hect_are.group(2))
            total = hectares + ares / 100.0
            if 0.01 <= total <= 500:
                return str(round(total, 2))
            logger.warning("Land area %s hectares is out of range", total)
            return None

        # Pattern 2: pure numeric with optional unit
        numeric = re.search(r'(\d+(?:\.\d+)?)', val_latin)
        if numeric:
            value = float(numeric.group(1))
            # Plausible single-farmer range: 0.01 to 500 hectares
            if 0.01 <= value <= 500:
                return str(round(value, 2))
            logger.warning("Land area %s is out of plausible range (0.01-500)", value)
            return None

        return None

