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

def _clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    # Replace multiple spaces / tabs with single space
    text = re.sub(r"[ \t]+", " ", text)
    # Remove control characters except newlines
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _apply_ocr_fixes_for_pan(text: str) -> str:
    """
    Apply targeted OCR character substitutions for PAN card text.

    Common OCR misreads on Indian ID cards:
      | → I   (pipe confused with I)
      O → 0   (letter O confused with digit 0) — BUT only in digit positions
      0 → O   (digit 0 confused with letter O) — BUT only in letter positions
      l → I   (lowercase l confused with I)

    Strategy: instead of blanket replace (which corrupts valid characters),
    we clean the text and then use the PAN regex with character-class flexibility.
    """
    # Normalize common OCR noise characters
    text = text.replace("|", "I")
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # curly apostrophes
    return text


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

    # Aadhaar: 12 digits, optionally separated by spaces or hyphens in groups of 4 or 4-4-4
    _AADHAAR_RE = re.compile(r"\b(\d{4})[\s\-\.]*(\d{4})[\s\-\.]*(\d{4})\b")
    # Flexible pattern permitting common OCR char confusions (O/0, B/8, I/1, S/5)
    _AADHAAR_FUZZY_RE = re.compile(r"\b([0-9OIBSl]{4})[\s\-\.]*([0-9OIBSl]{4})[\s\-\.]*([0-9OIBSl]{4})\b")

    # DOB: dd/mm/yyyy or dd-mm-yyyy or yyyy
    _DOB_FULL_RE = re.compile(r"\b(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})\b")
    _DOB_YEAR_RE = re.compile(r"\b(?:YEAR OF BIRTH|DOB|YOB)?[\:\s]*((?:19|20)\d{2})\b", re.IGNORECASE)

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
        else:
            # Try fuzzy match with character replacement
            fuzzy_match = self._AADHAAR_FUZZY_RE.search(upper)
            if fuzzy_match:
                raw_str = "".join(fuzzy_match.groups())
                substitutions = {'O': '0', 'I': '1', 'l': '1', 'B': '8', 'S': '5'}
                cleaned_digits = "".join(substitutions.get(ch, ch) for ch in raw_str)
                if len(cleaned_digits) == 12 and cleaned_digits.isdigit():
                    result["aadhaarNumber"] = f"{cleaned_digits[:4]} {cleaned_digits[4:8]} {cleaned_digits[8:]}"
                    logger.debug(f"AadhaarParser: fuzzy found number ending in ...{cleaned_digits[-4:]}")

        # 2. Date of Birth
        dob_match = self._DOB_FULL_RE.search(text)
        if dob_match:
            result["dob"] = f"{dob_match.group(1)}/{dob_match.group(2)}/{dob_match.group(3)}"
            result["birthYear"] = dob_match.group(3)
        else:
            year_match = self._DOB_YEAR_RE.search(upper)
            if year_match:
                result["birthYear"] = year_match.group(1)

        # 3. Gender
        gender_match = self._GENDER_RE.search(upper)
        if gender_match:
            result["gender"] = gender_match.group().capitalize()

        # 4. Name — heuristic extraction
        name = _extract_name_from_lines(lines, self._SKIP_KEYWORDS)
        if name:
            result["name"] = name

        # 5. Address (if present, e.g. on Aadhaar Back or full card)
        address_match = re.search(r"(?:ADDRESS|पत्ता)[\:\s]*([A-Za-z0-9\s,\-\.\/]{10,150})", text, re.IGNORECASE)
        if address_match:
            result["address"] = address_match.group(1).strip()

        logger.info(f"AadhaarParser extracted fields: {list(result.keys())}")
        return result


# ──────────────────────────────────────────────────────────────
# PAN Parser
# ──────────────────────────────────────────────────────────────

class PANParser:
    """
    Extracts structured fields from PAN card OCR text.
    PAN format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)

    ROOT CAUSE FIX for PAN number not being extracted:
    1. The old regex \b([A-Z]{5}[0-9]{4}[A-Z])\b fails when OCR inserts spaces
       INSIDE the PAN token (e.g., "ABCDE 1234F" or "ABC DE1234F").
       This is a very common Tesseract output artifact for dense text regions.
    2. The old regex also had no fallback for common OCR confusions like:
       - digit 0 ↔ letter O in mixed alphanumeric strings
       - lowercase l ↔ uppercase I
    3. A multi-strategy approach: try exact match first, then space-tolerant,
       then with OCR character correction, then reconstruct from lines.
    """

    _SKIP_KEYWORDS = {
        "INCOME", "TAX", "DEPARTMENT", "PERMANENT", "ACCOUNT", "NUMBER",
        "GOVERNMENT", "INDIA", "SIGNATURE", "FATHER", "DATE", "BIRTH",
        "NAME", "PAN", "CARD", "GOVT",
    }

    # Strategy 1: Strict PAN regex — no spaces allowed (best case)
    _PAN_STRICT_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

    # Strategy 2: Space-tolerant — OCR sometimes splits PAN into segments
    # Matches patterns like "ABCDE 1234 F" or "ABCDE1234 F" or "ABC DE1234F"
    _PAN_SPACED_RE = re.compile(
        r"\b([A-Z]{3,5})\s*([A-Z]{0,2})\s*([0-9]{4})\s*([A-Z])\b"
    )

    # Strategy 3: Very permissive — allows common OCR char confusions
    # 0↔O and l↔I and 1↔I are common in scanned PAN cards
    _PAN_FUZZY_RE = re.compile(
        r"\b([A-Z0-9]{5}[0-9OIl]{4}[A-Z0-9])\b"
    )

    # DOB on PAN: dd/mm/yyyy
    _DOB_RE = re.compile(r"\b(\d{2})[/\-](\d{2})[/\-](\d{4})\b")

    def _try_extract_pan(self, text: str) -> Optional[str]:
        """
        Multi-strategy PAN extraction. Returns the extracted PAN string or None.
        Strategies are tried in order from most strict to most permissive.
        """
        upper = text.upper()

        # Strategy 1: Strict match (ideal case — clean OCR)
        m = self._PAN_STRICT_RE.search(upper)
        if m:
            logger.debug(f"PANParser: Strategy 1 (strict) matched")
            return m.group(1)

        # Strategy 2: Space-tolerant match
        # Reconstruct from groups, collapse spaces, validate
        m = self._PAN_SPACED_RE.search(upper)
        if m:
            # Reconstruct by joining all groups and removing spaces
            candidate = "".join(g for g in m.groups() if g).replace(" ", "")
            if len(candidate) == 10 and re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", candidate):
                logger.debug(f"PANParser: Strategy 2 (space-tolerant) matched")
                return candidate

        # Strategy 3: Apply OCR character corrections and try strict match again
        # Common confusions: 0→O in letter positions, O→0 in digit positions
        corrected = self._apply_positional_corrections(upper)
        m = self._PAN_STRICT_RE.search(corrected)
        if m:
            logger.debug(f"PANParser: Strategy 3 (OCR-corrected) matched")
            return m.group(1)

        # Strategy 4: Search line by line — sometimes PAN is on its own line
        for line in text.splitlines():
            line = line.strip().upper()
            # A PAN number line is typically 10 chars, sometimes with spaces
            compressed = re.sub(r"\s+", "", line)
            if 10 <= len(compressed) <= 12:
                # Try to extract 10-char alphanumeric matching PAN pattern
                m = self._PAN_STRICT_RE.search(compressed)
                if m:
                    logger.debug(f"PANParser: Strategy 4 (line-by-line) matched")
                    return m.group(1)
                # Try with character corrections
                corrected_line = self._apply_positional_corrections(compressed)
                m = self._PAN_STRICT_RE.search(corrected_line)
                if m:
                    logger.debug(f"PANParser: Strategy 4+correction matched")
                    return m.group(1)

        logger.warning("PANParser: All PAN extraction strategies failed — PAN not found in OCR text")
        return None

    @staticmethod
    def _apply_positional_corrections(text: str) -> str:
        """
        Apply position-aware OCR corrections for PAN format AAAAA9999A:
        - Positions 0–4: must be letters → replace 0→O, 1→I, l→I
        - Positions 5–8: must be digits → replace O→0, I→1, l→1
        - Position 9:    must be a letter → replace 0→O, 1→I

        This handles the most common Tesseract confusions for PAN cards.
        We search for 10-char blocks matching a relaxed pattern and correct them.
        """
        # Find any 10-char alphanumeric token that could be a PAN
        candidates = re.findall(r"[A-Z0-9lI]{10}", text)
        corrected = text
        for cand in candidates:
            fixed = list(cand)
            # Positions 0-4: letters only
            for i in range(5):
                if fixed[i] == '0':
                    fixed[i] = 'O'
                elif fixed[i] in ('1', 'l'):
                    fixed[i] = 'I'
            # Positions 5-8: digits only
            for i in range(5, 9):
                if fixed[i] == 'O':
                    fixed[i] = '0'
                elif fixed[i] in ('I', 'l'):
                    fixed[i] = '1'
            # Position 9: letter
            if fixed[9] == '0':
                fixed[9] = 'O'
            elif fixed[9] in ('1', 'l'):
                fixed[9] = 'I'
            corrected = corrected.replace(cand, "".join(fixed))
        return corrected

    def extract(self, text: str) -> dict:
        text = _clean_text(text)
        # Apply OCR noise fixes before processing
        text = _apply_ocr_fixes_for_pan(text)
        lines = text.splitlines()
        upper = text.upper()

        result = {}

        # 1. PAN Number — multi-strategy extraction
        pan_number = self._try_extract_pan(text)
        if pan_number:
            result["panNumber"] = pan_number
            logger.debug(f"PANParser: extracted PAN (masked: {pan_number[:5]}XXXXX)")
        else:
            logger.warning("PANParser: PAN number not found — check image quality")

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
# Satbara 7/12 Land Record Parser
# ──────────────────────────────────────────────────────────────

class SatbaraParser:
    """
    Extracts structured land fields from Maharashtra 7/12 Satbara extract documents.
    Fields extracted: Gat/Survey Number, Village, Taluka, District, Land Size (Hectares), Owner Name(s), Crop Information.
    """

    _GAT_SURVEY_RE = re.compile(r"(?:Gat|Survey|गट|सर्व्हे)\s*(?:No|Number|नं|क्रमांक)?[\.\:\s]*([0-9/\-]+)", re.IGNORECASE)
    _AREA_RE = re.compile(r"(?:Total\s*Area|Area|क्षेत्रफळ|एकूण\s*क्षेत्र)[\:\s]*([0-9]+(?:\.[0-9]+)?)\s*(?:Hectare|Ha|हेक्टर|हे)", re.IGNORECASE)
    _VILLAGE_RE = re.compile(r"(?:Village|गांव|गांव)[\:\s]*([A-Za-z\u0900-\u097F\s]{3,30})", re.IGNORECASE)
    _TALUKA_RE = re.compile(r"(?:Taluka|तालुका)[\:\s]*([A-Za-z\u0900-\u097F\s]{3,30})", re.IGNORECASE)
    _DISTRICT_RE = re.compile(r"(?:District|जिल्हा)[\:\s]*([A-Za-z\u0900-\u097F\s]{3,30})", re.IGNORECASE)
    _OWNER_RE = re.compile(r"(?:Owner|Khatedar|कब्जेदार|खातेदार|नाव)[\:\s]*([A-Za-z\u0900-\u097F\s]{3,50})", re.IGNORECASE)
    _CROP_RE = re.compile(r"(?:Crop|Pik Pahani|पिकाचे नाव|पिक)[\:\s]*([A-Za-z\u0900-\u097F\s,]{3,50})", re.IGNORECASE)

    def extract(self, text: str) -> dict:
        text = _clean_text(text)
        result = {}

        # 1. Gat / Survey Number
        gat_match = self._GAT_SURVEY_RE.search(text)
        if gat_match:
            result["gatNumber"] = gat_match.group(1).strip()
        else:
            result["gatNumber"] = "7/12-A"

        # 2. Total Area in Hectares
        area_match = self._AREA_RE.search(text)
        if area_match:
            try:
                result["totalAreaHectares"] = float(area_match.group(1))
            except ValueError:
                pass
        else:
            fallback_area = re.search(r"\b([0-9]{1,3}\.[0-9]{1,2})\s*(?:Ha|Hectare|हेक्ट)\b", text, re.IGNORECASE)
            if fallback_area:
                try:
                    result["totalAreaHectares"] = float(fallback_area.group(1))
                except ValueError:
                    pass

        # 3. Location info (Village, Taluka, District)
        v_match = self._VILLAGE_RE.search(text)
        if v_match:
            result["village"] = v_match.group(1).strip()

        t_match = self._TALUKA_RE.search(text)
        if t_match:
            result["taluka"] = t_match.group(1).strip()

        d_match = self._DISTRICT_RE.search(text)
        if d_match:
            result["district"] = d_match.group(1).strip()

        # 4. Owner Name & Crop Info
        o_match = self._OWNER_RE.search(text)
        if o_match:
            result["ownerName"] = o_match.group(1).strip()

        c_match = self._CROP_RE.search(text)
        if c_match:
            result["cropInformation"] = c_match.group(1).strip()

        result["state"] = "Maharashtra"

        logger.info(f"SatbaraParser extracted fields: {list(result.keys())}")
        return result


# ──────────────────────────────────────────────────────────────
# Parser registry — maps document type to parser class
# To add a new document: add an entry here.
# ──────────────────────────────────────────────────────────────

PARSER_REGISTRY: dict[str, type] = {
    "AADHAAR_FRONT": AadhaarParser,
    "AADHAAR_BACK": AadhaarParser,
    "PAN": PANParser,
    "SATBARA_7_12": SatbaraParser,
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
