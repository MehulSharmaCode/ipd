"""
Unit tests for app.services.crawler.timeline_extractor.
"""
from datetime import date, datetime, timezone

from app.services.crawler.timeline_extractor import (
    build_application_timeline,
    evaluate_timeline_state,
    find_deadline_mentions,
    parse_source_date,
)

NOW = datetime(2026, 9, 8, 9, 14, 22, tzinfo=timezone.utc)


def test_parse_valid_iso_date():
    dt = parse_source_date("2019-02-24")
    assert dt == datetime(2019, 2, 24, tzinfo=timezone.utc)


def test_parse_non_iso_date_returns_none():
    assert parse_source_date("24/02/2019") is None


def test_parse_empty_or_none_returns_none():
    assert parse_source_date("") is None
    assert parse_source_date(None) is None
    assert parse_source_date("NA") is None


def test_open_date_only_is_open_ended():
    tl = build_application_timeline(
        open_date_raw="2019-02-24", close_date_raw=None,
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    assert tl["status"] == "open_ended"
    assert tl["open_date"] is not None
    assert tl["close_date"] is None


def test_open_and_close_date_is_window():
    tl = build_application_timeline(
        open_date_raw="2019-02-24", close_date_raw="2025-03-31",
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    assert tl["status"] == "window"


def test_neither_date_is_unknown():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw=None,
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    assert tl["status"] == "unknown"


def test_conflicting_dates_flagged_and_both_raws_kept():
    tl = build_application_timeline(
        open_date_raw="2025-03-31", close_date_raw="2019-02-24",
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    assert tl["status"] == "unknown"
    assert tl["open_date_raw"] == "2025-03-31"
    assert tl["close_date_raw"] == "2019-02-24"
    kinds = [m["kind"] for m in tl["text_mentions"]]
    assert "conflicting_dates" in kinds


def test_unparseable_close_date_preserves_raw_and_flags_mention():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw="31/03/2025",
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    assert tl["close_date"] is None
    assert tl["close_date_raw"] == "31/03/2025"
    kinds = [m["kind"] for m in tl["text_mentions"]]
    assert "unparseable_date" in kinds


def test_deadline_mention_never_produces_a_parsed_date():
    text = "Applications must be submitted before the last date notified by the department."
    mentions = find_deadline_mentions(text, None)
    assert len(mentions) == 1
    assert mentions[0]["kind"] == "deadline_phrase"
    assert "last date" in mentions[0]["excerpt"].lower()
    assert mentions[0]["field"] == "eligibility_raw"
    # This is the anti-fabrication check: the mention is a dict of only
    # {kind, excerpt, field} -- there is no date-shaped key anywhere.
    assert set(mentions[0].keys()) == {"kind", "excerpt", "field"}


def test_application_modes_carried_through_verbatim():
    tl = build_application_timeline(
        open_date_raw="2019-02-24", close_date_raw=None,
        application_process=[
            {"mode": "Online", "url": "https://pmkisan.gov.in/RegistrationFormnew.aspx"},
            {"mode": "Online - via CSC", "url": None},
        ],
        eligibility_raw=None, benefits_raw=None, fetched_at=NOW,
    )
    assert tl["application_modes"] == [
        {"mode": "Online", "url": "https://pmkisan.gov.in/RegistrationFormnew.aspx"},
        {"mode": "Online - via CSC", "url": None},
    ]


# --- evaluate_timeline_state: read-time derivation ---------------------------

def test_boundary_close_date_today_is_still_open_closing_soon():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw="2026-09-08",
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    state = evaluate_timeline_state(tl, today_ist=date(2026, 9, 8))
    assert state["state"] == "closing_soon"
    assert state["days_remaining"] == 0


def test_close_date_yesterday_is_expired():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw="2026-09-07",
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    state = evaluate_timeline_state(tl, today_ist=date(2026, 9, 8))
    assert state["state"] == "expired"
    assert state["days_remaining"] == -1


def test_close_date_far_future_is_open():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw="2026-12-31",
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    state = evaluate_timeline_state(tl, today_ist=date(2026, 9, 8))
    assert state["state"] == "open"
    assert state["days_remaining"] > 30


def test_open_ended_state():
    tl = build_application_timeline(
        open_date_raw="2019-02-24", close_date_raw=None,
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    state = evaluate_timeline_state(tl, today_ist=date(2026, 9, 8))
    assert state["state"] == "open_ended"
    assert state["days_remaining"] is None


def test_unknown_state_no_mentions():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw=None,
        application_process=None, eligibility_raw=None, benefits_raw=None,
        fetched_at=NOW,
    )
    state = evaluate_timeline_state(tl, today_ist=date(2026, 9, 8))
    assert state["state"] == "unknown"


def test_unknown_with_mention_state():
    tl = build_application_timeline(
        open_date_raw=None, close_date_raw=None,
        application_process=None,
        eligibility_raw="Applications close before the deadline notified separately.",
        benefits_raw=None, fetched_at=NOW,
    )
    state = evaluate_timeline_state(tl, today_ist=date(2026, 9, 8))
    assert state["state"] == "unknown_with_mention"


def test_none_timeline_is_unknown():
    state = evaluate_timeline_state(None, today_ist=date(2026, 9, 8))
    assert state["state"] == "unknown"
    assert state["days_remaining"] is None
