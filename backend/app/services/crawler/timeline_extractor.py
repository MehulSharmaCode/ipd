"""
Application Timeline Extractor
================================
Builds the `application_timeline` embedded sub-document (see
docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md section 5.2) from the raw date
strings and application-process data myScheme.gov.in publishes.

Hard rule (do not violate): a date is NEVER produced unless it was a literal
"YYYY-MM-DD" string in the source. Free-text deadline mentions are surfaced
as VERBATIM excerpts only -- this module never parses a date out of prose.

Expiry/closing-soon state is computed at READ TIME (evaluate_timeline_state),
never persisted, so it can never go stale in storage.
"""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo

    IST = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover - defensive fallback for a missing tzdata
    IST = timezone(timedelta(hours=5, minutes=30))

EXTRACTOR_VERSION = 1

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DEADLINE_PHRASES_RE = re.compile(
    r"(last date|closing date|deadline|apply before|due date|last day)",
    re.IGNORECASE,
)
EXCERPT_RADIUS = 120

# "closing soon" window, inclusive of the boundary day itself.
CLOSING_SOON_DAYS = 30


def parse_source_date(raw: Optional[str]) -> Optional[datetime]:
    """
    Strictly parse a literal "YYYY-MM-DD" source string into a UTC-midnight
    datetime. Anything else (different format, empty, None, "NA", partial
    dates) returns None -- this function never guesses.
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not _ISO_DATE_RE.match(raw):
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def find_deadline_mentions(
    eligibility_raw: Optional[str], benefits_raw: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Scan free text for deadline-related phrases and return VERBATIM excerpts
    around each match. Never parses a date out of the excerpt.
    """
    mentions: List[Dict[str, Any]] = []
    for field_name, text in (("eligibility_raw", eligibility_raw), ("benefits_raw", benefits_raw)):
        if not text:
            continue
        for match in DEADLINE_PHRASES_RE.finditer(text):
            start = max(0, match.start() - EXCERPT_RADIUS)
            end = min(len(text), match.end() + EXCERPT_RADIUS)
            excerpt = text[start:end].strip()
            excerpt = re.sub(r"\s+", " ", excerpt)
            mentions.append({
                "kind": "deadline_phrase",
                "excerpt": excerpt,
                "field": field_name,
            })
    return mentions


def build_application_timeline(
    *,
    open_date_raw: Optional[str],
    close_date_raw: Optional[str],
    application_process: Optional[list],
    eligibility_raw: Optional[str],
    benefits_raw: Optional[str],
    fetched_at: datetime,
) -> Dict[str, Any]:
    """
    Build the full `application_timeline` sub-document. Never raises.
    """
    open_date = parse_source_date(open_date_raw)
    close_date = parse_source_date(close_date_raw)

    text_mentions: List[Dict[str, Any]] = []

    if open_date_raw and open_date is None:
        text_mentions.append({
            "kind": "unparseable_date",
            "excerpt": f"schemeOpenDate: {open_date_raw}",
            "field": "scheme_open_date_raw",
        })
    if close_date_raw and close_date is None:
        text_mentions.append({
            "kind": "unparseable_date",
            "excerpt": f"schemeCloseDate: {close_date_raw}",
            "field": "scheme_close_date_raw",
        })

    if open_date is not None and close_date is not None and close_date < open_date:
        text_mentions.append({
            "kind": "conflicting_dates",
            "excerpt": f"open: {open_date_raw} / close: {close_date_raw}",
            "field": None,
        })
        status = "unknown"
    elif close_date is not None:
        status = "window"
    elif open_date is not None:
        status = "open_ended"
    else:
        status = "unknown"

    text_mentions.extend(find_deadline_mentions(eligibility_raw, benefits_raw))

    application_modes: List[Dict[str, Any]] = []
    for entry in application_process or []:
        if not isinstance(entry, dict):
            continue
        mode = entry.get("mode")
        if not mode:
            continue
        application_modes.append({"mode": mode, "url": entry.get("url")})

    return {
        "status": status,
        "open_date": open_date,
        "close_date": close_date,
        "open_date_raw": open_date_raw,
        "close_date_raw": close_date_raw,
        "open_date_source": "myscheme_basic_details.schemeOpenDate" if open_date_raw else None,
        "close_date_source": "myscheme_search_summary.schemeCloseDate" if close_date_raw else None,
        "application_modes": application_modes,
        "text_mentions": text_mentions,
        "fetched_at": fetched_at,
        "extractor_version": EXTRACTOR_VERSION,
    }


def _format_date(dt: datetime) -> str:
    return dt.strftime("%d %b %Y")


def evaluate_timeline_state(
    timeline: Optional[Dict[str, Any]], today_ist: Optional[date] = None
) -> Dict[str, Any]:
    """
    READ-TIME derivation of the display state for a stored application_timeline.
    Never persisted -- computed fresh on every read so it can never go stale.

    Returns {"state", "days_remaining", "label"}.
    """
    if today_ist is None:
        today_ist = datetime.now(IST).date()

    if not timeline:
        return {
            "state": "unknown",
            "days_remaining": None,
            "label": "Application deadline not published",
        }

    status = timeline.get("status")
    close_date = timeline.get("close_date")
    open_date = timeline.get("open_date")
    text_mentions = timeline.get("text_mentions") or []

    if status == "window" and close_date is not None:
        close_date_ist = close_date.astimezone(IST).date() if close_date.tzinfo else close_date.date()
        days_remaining = (close_date_ist - today_ist).days
        if days_remaining < 0:
            return {
                "state": "expired",
                "days_remaining": days_remaining,
                "label": f"Closed on {_format_date(close_date)}",
            }
        if days_remaining <= CLOSING_SOON_DAYS:
            return {
                "state": "closing_soon",
                "days_remaining": days_remaining,
                "label": f"Closes in {days_remaining} day{'s' if days_remaining != 1 else ''}"
                if days_remaining > 0 else "Closes today",
            }
        return {
            "state": "open",
            "days_remaining": days_remaining,
            "label": f"Apply by {_format_date(close_date)}",
        }

    if status == "open_ended":
        return {
            "state": "open_ended",
            "days_remaining": None,
            "label": "Open — no closing date published",
        }

    # status == "unknown"
    if text_mentions:
        return {
            "state": "unknown_with_mention",
            "days_remaining": None,
            "label": "See official page for dates",
        }

    return {
        "state": "unknown",
        "days_remaining": None,
        "label": "Application deadline not published",
    }
