"""
myScheme.gov.in Response Parser
--------------------------------
Extracts structured fields from the myScheme API JSON responses.
Adapted from the reference myscheme_ingest.py normalize_scheme() function,
split into a parser that extracts raw fields, and a normalizer that maps
them to the internal DB schema.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MySchemeParser:
    """Parses raw myScheme API JSON into intermediate scheme dicts."""

    @staticmethod
    def parse_summary(item_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse one item from the search endpoint's data.hits.items[].fields.
        Returns an intermediate dict with the raw myScheme fields.
        """
        return {
            "myscheme_id": item_fields.get("_id"),
            "slug": item_fields.get("slug"),
            "scheme_name": item_fields.get("schemeName"),
            "short_title": item_fields.get("schemeShortTitle"),
            "level": item_fields.get("level"),
            "ministry": item_fields.get("nodalMinistryName"),
            "categories": item_fields.get("schemeCategory", []),
            "tags": item_fields.get("tags", []),
            "beneficiary_states": item_fields.get("beneficiaryState", []),
            "brief_description": item_fields.get("briefDescription"),
            "close_date": item_fields.get("schemeCloseDate"),
        }

    @staticmethod
    def parse_detail(detail_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the full detail response from /schemes/v6/public/schemes.
        Returns additional fields that aren't in the search summary.
        """
        en = (detail_payload.get("data") or {}).get("en") or {}
        basic = en.get("basicDetails") or {}
        content = en.get("schemeContent") or {}
        eligibility = en.get("eligibilityCriteria") or {}

        target_beneficiaries = []
        raw_beneficiaries = basic.get("targetBeneficiaries") or []
        for b in raw_beneficiaries:
            label = b.get("label") if isinstance(b, dict) else str(b)
            if label:
                target_beneficiaries.append(label)

        benefit_types_raw = content.get("benefitTypes")
        benefit_type_label = None
        if isinstance(benefit_types_raw, dict):
            benefit_type_label = benefit_types_raw.get("label")
        elif isinstance(benefit_types_raw, list) and benefit_types_raw:
            benefit_type_label = benefit_types_raw[0].get("label") if isinstance(benefit_types_raw[0], dict) else str(benefit_types_raw[0])

        scheme_type_raw = basic.get("schemeType")
        scheme_type_label = None
        if isinstance(scheme_type_raw, dict):
            scheme_type_label = scheme_type_raw.get("label")

        return {
            "implementing_agency": basic.get("implementingAgency"),
            "scheme_type": scheme_type_label,
            "scheme_open_date": basic.get("schemeOpenDate"),
            "target_beneficiaries": target_beneficiaries,
            "detailed_description_md": content.get("detailedDescription_md"),
            "benefits_md": content.get("benefits_md"),
            "exclusions_md": content.get("exclusions_md"),
            "benefit_type_label": benefit_type_label,
            "eligibility_description_md": eligibility.get("eligibilityDescription_md"),
            "application_process": en.get("applicationProcess", []),
        }

    @staticmethod
    def merge_summary_and_detail(summary: Dict[str, Any],
                                  detail_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine parsed summary + detail into one intermediate record.
        """
        merged = dict(summary)
        if detail_payload:
            detail_fields = MySchemeParser.parse_detail(detail_payload)
            merged.update(detail_fields)
        return merged
