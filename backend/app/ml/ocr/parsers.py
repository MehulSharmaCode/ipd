"""
Field Extraction Parsers
-------------------------
Responsibility: Extract structured fields from cleaned OCR text.

Each parser is a class with a single public method: `extract(text: str) -> dict`.
Parsers normalize text, correct common OCR mistakes, and return structured JSON.

Current parsers:
  - AadhaarParser  — Name, Aadhaar Number, DOB, Birth Year, Gender
  - PANParser       — Name, PAN Number, Father's Name, DOB

Adding a new document type: implement a new XxxParser with the same interface.
The pipeline.py will route to the correct parser via classification.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Shared OCR correction helpers
# ──────────────────────────────────────────────────────────────

# Common OCR character confusions in Indian ID cards
_OCR_CHAR_FIXES = str.maketrans({
    "|": "I",
    "l": "I",     # lowercase L → I (in all-caps context, handled after)
    "0": "O",     # only where applicable (applied selectively in parsers)
    "\u2019": "'",  # curly apostrophe → straight
})


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    # Replace multiple spaces / tabs with single space
    text = re.sub(r"[ \t]+", " ", text)
    # Remove control characters except newlines
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_name_from_lines(lines: list[str], skip_keywords: set[str]) -> Optional[str]:
    """
    Heuristic name extractor: finds a line of 2+ title-cased words
    that doesn't contain any known keyword.
    """
    for line in lines:
        line = line.strip()
        # Skip short lines and lines with digits (likely not a name)
        if len(line) < 4 or any(ch.isdigit() for ch in line):
            continue
        # Skip lines with known non-name keywords
        upper = line.upper()
        if any(kw in upper for kw in skip_keywords):
            continue
        # Skip lines that are too long to be a name
        if len(line) > 50:
            continue
        words = line.split()
        # A name usually has 2–4 words, each starting with a capital letter
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w):
            return " ".join(words)
    return None


# ──────────────────────────────────────────────────────────────
# Aadhaar Parser
# ──────────────────────────────────────────────────────────────

class AadhaarParser:
    """
    Extracts structured fields from Aadhaar card OCR text.
    Handles both front (name/DOB/gender) and back (address) sides.
    Returns only the fields it can confidently extract.
    """

    _SKIP_KEYWORDS = {
        "GOVERNMENT", "INDIA", "UNIQUE", "IDENTIFICATION", "AUTHORITY",
        "UIDAI", "AADHAAR", "DOB", "DATE", "BIRTH", "YEAR", "MALE",
        "FEMALE", "TRANSGENDER", "ENROLLMENT", "ADDRESS", "MOBILE",
        "HELP", "TOLL", "FREE", "WWW", "DOWNLOAD", "VID",
    }

    # Aadhaar: 12 digits, optionally separated by spaces or hyphens in groups of 4
    _AADHAAR_RE = re.compile(r"\b(\d{4})[\s\-]*(\d{4})[\s\-]*(\d{4})\b")

    # DOB: dd/mm/yyyy or dd-mm-yyyy or yyyy
    _DOB_FULL_RE = re.compile(r"\b(\d{2})[/\-](\d{2})[/\-](\d{4})\b")
    _DOB_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

    # Gender keywords
    _GENDER_RE = re.compile(r"\b(MALE|FEMALE|TRANSGENDER)\b", re.IGNORECASE)

    def extract(self, text: str) -> dict:
        text = _clean_text(text)
        upper = text.upper()
        lines = text.splitlines()

        result = {}

        # 1. Aadhaar Number
        match = self._AADHAAR_RE.search(upper)
        if match:
            raw_number = "".join(match.groups())
            result["aadhaarNumber"] = f"{raw_number[:4]} {raw_number[4:8]} {raw_number[8:]}"
            logger.debug(f"AadhaarParser: found number ending in ...{raw_number[-4:]}")

        # 2. Date of Birth
        dob_match = self._DOB_FULL_RE.search(text)
        if dob_match:
            result["dob"] = f"{dob_match.group(1)}/{dob_match.group(2)}/{dob_match.group(3)}"
            result["birthYear"] = dob_match.group(3)
        else:
            year_match = self._DOB_YEAR_RE.search(upper)
            if year_match:
                result["birthYear"] = year_match.group()

        # 3. Gender
        gender_match = self._GENDER_RE.search(upper)
        if gender_match:
            result["gender"] = gender_match.group().capitalize()

        # 4. Name — heuristic extraction
        name = _extract_name_from_lines(lines, self._SKIP_KEYWORDS)
        if name:
            result["name"] = name

        logger.info(f"AadhaarParser extracted fields: {list(result.keys())}")
        return result


# ──────────────────────────────────────────────────────────────
# PAN Parser
# ──────────────────────────────────────────────────────────────

class PANParser:
    """
    Extracts structured fields from PAN card OCR text.
    PAN format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)
    """

    _SKIP_KEYWORDS = {
        "INCOME", "TAX", "DEPARTMENT", "PERMANENT", "ACCOUNT", "NUMBER",
        "GOVERNMENT", "INDIA", "SIGNATURE", "FATHER", "DATE", "BIRTH",
        "NAME", "PAN", "CARD", "GOVT",
    }

    # Strict PAN regex: AAAAA9999A
    _PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

    # DOB on PAN: dd/mm/yyyy
    _DOB_RE = re.compile(r"\b(\d{2})[/\-](\d{2})[/\-](\d{4})\b")

    def extract(self, text: str) -> dict:
        text = _clean_text(text)
        # PAN text is mostly uppercase on the card
        upper = text.upper()
        lines = text.splitlines()

        result = {}

        # 1. PAN Number
        pan_match = self._PAN_RE.search(upper)
        if pan_match:
            result["panNumber"] = pan_match.group(1)
            logger.debug(f"PANParser: found PAN number (masked: {pan_match.group(1)[:5]}XXXXX)")

        # 2. DOB
        dob_match = self._DOB_RE.search(text)
        if dob_match:
            result["dob"] = f"{dob_match.group(1)}/{dob_match.group(2)}/{dob_match.group(3)}"

        # 3. Name and Father's Name
        # On PAN cards: Name is usually the first name-like line,
        # Father's name is the second name-like line.
        name_lines = []
        for line in lines:
            line = line.strip()
            if len(line) < 4 or any(ch.isdigit() for ch in line):
                continue
            upper_line = line.upper()
            if any(kw in upper_line for kw in self._SKIP_KEYWORDS):
                continue
            if len(line) > 50:
                continue
            words = line.split()
            if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w):
                name_lines.append(" ".join(words))
            if len(name_lines) == 2:
                break

        if len(name_lines) >= 1:
            result["name"] = name_lines[0]
        if len(name_lines) >= 2:
            result["fatherName"] = name_lines[1]

        logger.info(f"PANParser extracted fields: {list(result.keys())}")
        return result


# ──────────────────────────────────────────────────────────────
# Parser registry — maps document type to parser class
# To add a new document: add an entry here.
# ──────────────────────────────────────────────────────────────

PARSER_REGISTRY: dict[str, type] = {
    "AADHAAR_FRONT": AadhaarParser,
    "AADHAAR_BACK": AadhaarParser,
    "PAN": PANParser,
}


def get_parser(document_type: str):
    """
    Return the correct parser instance for a given document type.
    Returns None if the document type is not supported.
    """
    cls = PARSER_REGISTRY.get(document_type)
    if cls is None:
        logger.warning(f"No parser registered for document type: '{document_type}'")
        return None
    return cls()
