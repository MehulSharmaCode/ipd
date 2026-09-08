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

        # myscheme_object_id is the Mongo ObjectId identifying this scheme in
        # myScheme's own database (detail["data"]["_id"]). It is NOT the same
        # as myscheme_id (the search endpoint's Elasticsearch id) -- this is
        # the id the /documents, /faqs and /applicationchannel sub-resource
        # endpoints require.
        myscheme_object_id = (detail_payload.get("data") or {}).get("_id")

        # Reduced {mode, url} view of applicationProcess, used by the
        # application-timeline enrichment. application_process (below) keeps
        # the full raw entries (including step-by-step process content) for
        # any future consumer that needs them.
        application_modes = [
            {"mode": ap.get("mode"), "url": ap.get("url")}
            for ap in (en.get("applicationProcess") or [])
            if isinstance(ap, dict) and ap.get("mode")
        ]

        return {
            "myscheme_object_id": myscheme_object_id,
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
            "application_modes": application_modes,
        }

    @staticmethod
    def parse_documents(documents_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Narrow a raw GET .../{id}/documents response to just the 'en' section
        needed by document_extractor.build_required_documents(), or None when
        the scheme has no documents section (payload missing or data is null).
        """
        if not documents_payload or not isinstance(documents_payload, dict):
            return None
        data = documents_payload.get("data")
        if not isinstance(data, dict):
            return None
        en = data.get("en")
        if not isinstance(en, dict):
            return None
        return {
            "documentsRequired_md": en.get("documentsRequired_md"),
            "documents_required": en.get("documents_required"),
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
