"""
Required Documents Extractor
==============================
Turns a myScheme.gov.in `/schemes/v6/public/schemes/{id}/documents` API payload
into the `required_documents` embedded sub-document stored on a scheme (see
docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md section 5.1).

Design rules (do not violate):
  - `raw_text` is always the verbatim (HTML-unescaped, link-stripped) source
    line. It is the value displayed to the user; it is never fabricated.
  - `doc_type` / `match_confidence` are DERIVED classification metadata from
    document_taxonomy.classify_document() -- never shown as text themselves.
  - Every function here is pure and never raises: malformed or missing input
    degrades to an honest "unavailable" status, never a guessed value.
"""

import html
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.crawler.document_taxonomy import classify_document

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = 1

# Longest/most-specific patterns first -- the first pattern that matches wins.
CONDITIONAL_PATTERNS = [
    r"\(\s*if\s+applicable\s*\)",
    r"\(\s*if\s+any\s*\)",
    r"\(\s*if\s+[^)]{1,80}\)",
    r"\bif\s+applicable\b",
    r"\bwherever\s+applicable\b",
    r"\bas\s+applicable\b",
    r"\(\s*for\s+[^)]{1,80}\)",
    r"\bfor\s+(?:sc|st|obc|minority|apst|pwd)\b[^,.;]{0,40}",
    r"\bor\s+equivalent\b",
    r"\bany\s+other\s+documents?\b",
]
_CONDITIONAL_RE = [re.compile(p, re.IGNORECASE) for p in CONDITIONAL_PATTERNS]

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_LEADING_MARKER_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s*")
_WHITESPACE_RE = re.compile(r"\s+")
# Bare formatting artifacts left over from myScheme's markdown+HTML hybrid
# fields (e.g. a trailing "<br>" line) -- not real document requirements.
_HTML_TAG_ONLY_RE = re.compile(r"^</?[a-zA-Z][a-zA-Z0-9]*\s*/?>$")

# Splits a markdown list into items on any '<digits>.<space>' or '<digits>)<space>'
# marker, even when NOT preceded by whitespace/newline -- myScheme sometimes omits
# the newline between consecutive list items when the previous item ends in a
# markdown link, producing a run-on like:
#   "1. [Undertaking](url)1. [Work Slip](url)1. Proof of residence"
_INLINE_MARKER_SPLIT_RE = re.compile(r"(?=\d+[.)]\s)")

MAX_ITEMS = 40
MIN_ITEM_LENGTH = 3


def flatten_documents_ast(nodes: Optional[list]) -> List[str]:
    """
    Walk the Slate-style AST returned in documents_required, returning one
    raw string per node with type == "list_item" (its text runs joined).
    """
    if not nodes:
        return []

    def collect_text(children: Optional[list]) -> List[str]:
        out = []
        for child in children or []:
            if not isinstance(child, dict):
                continue
            if "text" in child:
                out.append(child["text"])
            if child.get("children"):
                out.extend(collect_text(child["children"]))
        return out

    items: List[str] = []

    def walk(node_list: Optional[list]) -> None:
        for node in node_list or []:
            if not isinstance(node, dict):
                continue
            if node.get("type") == "list_item":
                text = "".join(collect_text(node.get("children")))
                if text.strip():
                    items.append(text.strip())
            elif node.get("children"):
                walk(node["children"])

    walk(nodes)
    return items


def parse_documents_markdown(md: Optional[str]) -> List[str]:
    """
    Parse an ordered/unordered markdown list into one raw string per item.
    Handles myScheme's occasional malformed run-on lists where the newline
    between two "N. " markers is missing (see module docstring).
    """
    if not md:
        return []

    raw_items: List[str] = []
    for line in md.split("\n"):
        if not line.strip():
            continue
        for part in _INLINE_MARKER_SPLIT_RE.split(line):
            if part.strip():
                raw_items.append(part)

    cleaned: List[str] = []
    for item in raw_items:
        stripped = _LEADING_MARKER_RE.sub("", item).strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _detect_condition(text: str) -> Tuple[str, Optional[str], str]:
    """
    Returns (requirement, condition_text, display_name) for a cleaned working
    string. Tries CONDITIONAL_PATTERNS in order; the first match wins.
    """
    for pattern in _CONDITIONAL_RE:
        match = pattern.search(text)
        if not match:
            continue
        span_text = match.group(0).strip()
        condition_text = span_text.strip("()").strip()
        display_name = (text[: match.start()] + text[match.end():]).strip()
        display_name = _WHITESPACE_RE.sub(" ", display_name).strip()
        if not display_name:
            display_name = text
        return "conditional", condition_text, display_name

    return "mandatory", None, text


def normalize_document_line(raw: str) -> Optional[Dict[str, Any]]:
    """
    Convert one raw document-requirement line into an `items[]` entry
    (see section 5.1 of the feature plan). Returns None for empty/junk lines.
    """
    if not raw or not raw.strip():
        return None

    text = raw
    # HTML-unescape repeatedly -- the source is sometimes multiply-escaped
    # (observed: "&amp;amp;#39;", which needs 3 passes to fully resolve to
    # an apostrophe). Bounded at 5 passes and stops early once a pass is a
    # no-op, so this can never loop on adversarial/pathological input.
    for _ in range(5):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped

    # Extract markdown links; replace "[label](url)" with just "label".
    links: List[str] = []

    def _replace_link(m: "re.Match[str]") -> str:
        label, url = m.group(1), m.group(2)
        url = url.strip()
        if url.startswith("http://") or url.startswith("https://"):
            links.append(url)
        return label

    text = _LINK_RE.sub(_replace_link, text)

    # Strip a leading list marker (defensive -- normally already stripped by
    # the caller, but a nested/run-on split can leave one behind).
    text = _LEADING_MARKER_RE.sub("", text)

    # Collapse whitespace.
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return None

    # Drop bare HTML formatting artifacts (e.g. a lone "<br>" line) -- these
    # are not document requirements, just leftover markup from the source.
    if _HTML_TAG_ONLY_RE.match(text):
        return None

    # raw_text is the value BEFORE trailing-dot stripping -- the verbatim
    # (post-unescape, post-link-extraction) source line.
    raw_text = text

    # Strip a single trailing '.' only when it is the ONLY '.' in the string,
    # so "Aadhaar Card." -> "Aadhaar Card" but "Rs. 5 lakh proof." keeps its dots.
    working = text
    if working.endswith(".") and working.count(".") == 1:
        working = working[:-1].strip()

    if len(working) < MIN_ITEM_LENGTH:
        return None

    requirement, condition_text, display_name = _detect_condition(working)

    doc_type, match_confidence = classify_document(display_name or working)
    if doc_type == "UNKNOWN":
        display_name = working

    return {
        "raw_text": raw_text,
        "display_name": display_name,
        "doc_type": doc_type,
        "requirement": requirement,
        "condition_text": condition_text,
        "match_confidence": match_confidence,
        "links": links,
    }


def _empty_required_documents(status: str, *, source_url: Optional[str],
                               fetched_at: datetime,
                               raw_markdown: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status": status,
        "source": "myscheme_documents_api",
        "source_url": source_url,
        "fetched_at": fetched_at,
        "raw_markdown": raw_markdown,
        "items": [],
        "item_count": 0,
        "unmatched_count": 0,
        "extractor_version": EXTRACTOR_VERSION,
    }


def build_required_documents(
    documents_payload: Optional[Dict[str, Any]],
    *,
    source_url: Optional[str],
    fetched_at: datetime,
    fetch_failed: bool = False,
) -> Dict[str, Any]:
    """
    Build the full `required_documents` sub-document (section 5.1) from a raw
    /documents API response. Never raises.
    """
    if fetch_failed:
        return _empty_required_documents("fetch_failed", source_url=source_url,
                                          fetched_at=fetched_at)

    if not documents_payload or not isinstance(documents_payload, dict):
        return _empty_required_documents("unavailable", source_url=source_url,
                                          fetched_at=fetched_at)

    data = documents_payload.get("data")
    if not isinstance(data, dict):
        return _empty_required_documents("unavailable", source_url=source_url,
                                          fetched_at=fetched_at)

    en = data.get("en")
    if not isinstance(en, dict):
        return _empty_required_documents("unavailable", source_url=source_url,
                                          fetched_at=fetched_at)

    raw_markdown = en.get("documentsRequired_md")
    ast_nodes = en.get("documents_required")

    raw_lines = flatten_documents_ast(ast_nodes)
    if not raw_lines:
        raw_lines = parse_documents_markdown(raw_markdown)

    # De-duplicate by case-folded raw_text, preserving first-seen order, BEFORE
    # applying the 40-item cap -- item_count reflects the true (deduplicated)
    # source count even when more than MAX_ITEMS items were returned.
    deduped: List[Dict[str, Any]] = []
    seen: set = set()

    for raw_line in raw_lines:
        entry = normalize_document_line(raw_line)
        if entry is None:
            continue
        key = entry["raw_text"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)

    if not deduped:
        return _empty_required_documents("unavailable", source_url=source_url,
                                          fetched_at=fetched_at,
                                          raw_markdown=raw_markdown)

    items = deduped[:MAX_ITEMS]
    unmatched_count = sum(1 for i in items if i["doc_type"] == "UNKNOWN")

    return {
        "status": "available",
        "source": "myscheme_documents_api",
        "source_url": source_url,
        "fetched_at": fetched_at,
        "raw_markdown": raw_markdown,
        "items": items,
        "item_count": len(deduped),
        "unmatched_count": unmatched_count,
        "extractor_version": EXTRACTOR_VERSION,
    }
