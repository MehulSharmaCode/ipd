"""
Scheme Normalizer — myScheme → Internal DB Schema
---------------------------------------------------
Converts parsed myScheme records into the exact schema used by the
MongoDB `schemes` collection and consumed by the ML pipeline.

ML layer expects:  scheme_id, name, rules[], conflicts_with[],
                   benefit_calculation{}, (optional) financial_benefit

Since myScheme provides free-text eligibility only, ingested schemes
get empty rules[] and default benefit_calculation until an admin adds
structured data. The raw eligibility and benefits markdown are preserved
in eligibility_raw / benefits_raw for reference.
"""

import re
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MySchemeNormalizer:
    """Normalizes parsed myScheme records into the internal DB scheme schema."""

    @staticmethod
    def slug_to_scheme_id(slug: str) -> str:
        """
        Convert a myScheme slug to a scheme_id matching internal conventions.
        E.g. 'pradhan-mantri-kisan-samman-nidhi' → 'PRADHAN_MANTRI_KISAN_SAMMAN_NIDHI'
        """
        if not slug:
            return "UNKNOWN_SCHEME"
        # Replace hyphens with underscores, strip non-alphanumeric, uppercase
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", slug.replace("-", "_"))
        clean = re.sub(r"_+", "_", clean).strip("_")
        return clean.upper()

    @staticmethod
    def determine_level(raw_level: str, beneficiary_states: list) -> str:
        """Map myScheme level string to our 'central' / 'state' enum."""
        beneficiary_states = beneficiary_states or []
        if not raw_level:
            return "central"
        low = str(raw_level).lower()
        if "state" in low:
            return "state"
        if "central" in low or "national" in low:
            return "central"
        # If beneficiary_states has specific states and not "All", likely state-level
        if beneficiary_states and "All" not in beneficiary_states:
            return "state"
        return "central"

    @staticmethod
    def pick_first_state(beneficiary_states: list) -> str | None:
        """Extract a single state name, or None if central/all."""
        beneficiary_states = beneficiary_states or []
        filtered = [s for s in beneficiary_states if s and str(s).lower() not in ("all", "na")]
        return filtered[0] if filtered else None

    @staticmethod
    def pick_category(categories: list) -> str:
        """Pick the best category, preferring Agriculture-related ones."""
        categories = categories or []
        if not categories:
            return "General"
        # Prefer agriculture-related category if present
        for cat in categories:
            if cat and any(kw in str(cat).lower() for kw in ("agri", "farm", "rural", "crop", "irrigation")):
                return str(cat)
        return str(categories[0]) if categories[0] else "General"

    @staticmethod
    def compute_content_hash(record: Dict[str, Any]) -> str:
        """Hash key content fields for change detection."""
        hashable = (
            str(record.get("name", "")) +
            str(record.get("description", "")) +
            str(record.get("eligibility_raw", ""))
        )
        return hashlib.sha256(hashable.encode("utf-8")).hexdigest()

    def normalize(self, parsed_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a parsed myScheme record to the internal scheme DB schema.

        The output matches SchemeBase in app/models/scheme.py and is directly
        consumable by the ML pipeline (RulesEngine, KnowledgeGraph, BenefitPredictor).
        """
        slug = parsed_record.get("slug", "")
        scheme_id = self.slug_to_scheme_id(slug)
        categories = parsed_record.get("categories") or []
        beneficiary_states = parsed_record.get("beneficiary_states") or []
        level = self.determine_level(parsed_record.get("level", ""), beneficiary_states)

        # Build description from brief + detailed if available
        brief = parsed_record.get("brief_description") or ""
        detailed_md = parsed_record.get("detailed_description_md") or ""
        description = brief if brief else (detailed_md[:500] if detailed_md else "Government scheme")

        now = datetime.utcnow()

        normalized = {
            # --- Fields consumed by ML pipeline ---
            "scheme_id": scheme_id,
            "name": parsed_record.get("scheme_name") or slug,
            "rules": [],                                          # Cannot auto-extract from free text
            "conflicts_with": [],                                 # No conflict data in myScheme API
            "benefit_calculation": {"type": "flat_rate", "base_rate": 0},  # Default — admin sets real values

            # --- Fields for API/UI (SchemeBase model) ---
            "department": parsed_record.get("ministry") or "Government of India",
            "description": description,
            "category": self.pick_category(categories),
            "level": level,
            "state": self.pick_first_state(beneficiary_states),
            "benefit_type": parsed_record.get("benefit_type_label") or "Government Benefit",
            "status": "published",                           # Live and accessible for ML rules matching
            "source_url": f"https://www.myscheme.gov.in/schemes/{slug}" if slug else None,

            # --- New fields for myScheme tracking ---
            "myscheme_slug": slug,
            "myscheme_tags": parsed_record.get("tags", []),
            "eligibility_raw": parsed_record.get("eligibility_description_md") or "",
            "benefits_raw": parsed_record.get("benefits_md") or "",
            "last_fetched": now,
            "content_hash": "",  # set below
            "updated_at": now,
        }

        normalized["content_hash"] = self.compute_content_hash(normalized)
        return normalized
