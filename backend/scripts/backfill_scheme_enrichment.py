"""
Backfill: required_documents + application_timeline enrichment
=================================================================
One-shot script that enriches schemes already stored in MongoDB (from before
this feature existed) with `required_documents` and `application_timeline`,
without waiting for the daily ingestion cycle's 24h freshness cache to expire.

This does NOT touch `rules`, `benefit_calculation`, or trigger the (broken)
Gemini rule extractor -- it only fetches scheme detail + documents and writes
the two new enrichment sub-documents, exactly like a normal ingestion cycle
would, but on demand and without re-running rule extraction.

Usage:
    python scripts/backfill_scheme_enrichment.py [--limit N] [--slug SLUG ...]
        [--dry-run] [--force] [--concurrency N] [--offline]

Resumable: re-running with no flags only processes schemes that still need
enrichment (see SELECTION_QUERY below), so an interrupted run can simply be
re-invoked.
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend root directory to sys.path (mirrors scripts/seed_schemes.py)
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.crawler.fetcher import MySchemeApiFetcher  # noqa: E402
from app.services.crawler.parser import MySchemeParser  # noqa: E402
from app.services.crawler.document_extractor import (  # noqa: E402
    build_required_documents,
    EXTRACTOR_VERSION as DOC_EXTRACTOR_VERSION,
)
from app.services.crawler.timeline_extractor import build_application_timeline  # noqa: E402

import httpx  # noqa: E402


def selection_query(force: bool) -> Dict[str, Any]:
    """
    Schemes needing enrichment: no required_documents yet, a previous fetch
    failed / was never attempted, or the extractor taxonomy has moved on to a
    newer version than what's stored. --force drops this filter entirely.
    """
    if force:
        return {}
    return {
        "$or": [
            {"required_documents": {"$exists": False}},
            {"required_documents.status": {"$in": ["fetch_failed", "not_fetched"]}},
            {"required_documents.extractor_version": {"$ne": DOC_EXTRACTOR_VERSION}},
        ]
    }


def _no_source_documents(fetched_at: datetime) -> Dict[str, Any]:
    """required_documents value for a scheme that didn't come from myScheme
    at all (e.g. one of the YAML-seeded rows with myscheme_slug == None)."""
    return {
        "status": "unavailable",
        "source": "not_from_myscheme",
        "source_url": None,
        "fetched_at": fetched_at,
        "raw_markdown": None,
        "items": [],
        "item_count": 0,
        "unmatched_count": 0,
        "extractor_version": DOC_EXTRACTOR_VERSION,
    }


async def _process_one(
    db,
    doc: Dict[str, Any],
    fetcher: MySchemeApiFetcher,
    client: Optional[httpx.AsyncClient],
    *,
    offline: bool,
    dry_run: bool,
    stats: Dict[str, int],
) -> None:
    slug = doc.get("myscheme_slug")
    now = datetime.utcnow()

    if not slug:
        # Not a myScheme-sourced row (e.g. YAML-seeded) -- nothing to fetch.
        update = {
            "required_documents": _no_source_documents(now),
            "application_timeline": {
                "status": "unknown", "open_date": None, "close_date": None,
                "open_date_raw": None, "close_date_raw": None,
                "open_date_source": None, "close_date_source": None,
                "application_modes": [], "text_mentions": [], "fetched_at": now,
                "extractor_version": 1,
            },
        }
        stats["no_source"] += 1
        if not dry_run:
            await db["schemes"].update_one({"_id": doc["_id"]}, {"$set": update})
        return

    object_id = doc.get("myscheme_object_id")
    open_date_raw = doc.get("scheme_open_date_raw")
    # NOTE: schemeCloseDate is only present on the *search* endpoint's
    # summary fields, never on the detail payload -- verified during the
    # source-data audit (docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sec. 2.2).
    # This script deliberately does not re-scan the full paginated search
    # index just to discover close dates (only ~0.5% of schemes have one,
    # and doing so would multiply this script's runtime). For a scheme this
    # backfill reaches before its next normal ingestion cycle, close_date_raw
    # stays whatever was already stored (often None) until the daily
    # scheduler run touches it and populates it from the search summary.
    close_date_raw = doc.get("scheme_close_date_raw")
    application_modes = (doc.get("application_timeline") or {}).get("application_modes") or []
    source_url = doc.get("source_url") or f"https://www.myscheme.gov.in/schemes/{slug}"

    required_documents: Dict[str, Any]

    if offline:
        # No HTTP at all: derive the timeline from whatever is already
        # stored, and leave required_documents untouched (or "not_fetched"
        # if there was never one) -- it genuinely requires a network call.
        required_documents = doc.get("required_documents") or {
            "status": "not_fetched", "source": None, "source_url": source_url,
            "fetched_at": None, "raw_markdown": None, "items": [], "item_count": 0,
            "unmatched_count": 0, "extractor_version": DOC_EXTRACTOR_VERSION,
        }
    else:
        assert client is not None
        # Always fetch a fresh detail payload -- it is the authoritative
        # source for myscheme_object_id / scheme_open_date / application
        # modes, and is cheap (one GET) even when we already had an object_id.
        detail_payload = await fetcher.fetch_scheme_detail(client, slug)
        if detail_payload is not None:
            parsed_detail = MySchemeParser.parse_detail(detail_payload)
            object_id = parsed_detail.get("myscheme_object_id") or object_id
            open_date_raw = parsed_detail.get("scheme_open_date") or open_date_raw
            application_modes = parsed_detail.get("application_modes") or application_modes
            await asyncio.sleep(0.5)

        fetch_failed = False
        documents_payload = None
        if object_id:
            documents_payload = await fetcher.fetch_scheme_documents(client, object_id)
            fetch_failed = documents_payload is None
            await asyncio.sleep(0.5)
        else:
            fetch_failed = True  # never had an id to ask with -> treat as a failed attempt

        required_documents = build_required_documents(
            documents_payload, source_url=source_url, fetched_at=now,
            fetch_failed=fetch_failed,
        )

    application_timeline = build_application_timeline(
        open_date_raw=open_date_raw,
        close_date_raw=close_date_raw,
        application_process=application_modes,
        eligibility_raw=doc.get("eligibility_raw"),
        benefits_raw=doc.get("benefits_raw"),
        fetched_at=now,
    )

    # Same enrichment write policy as the scheduler: manually_verified locks
    # both sub-documents; a fresh fetch_failed never clobbers prior "available"
    # documents.
    if doc.get("manually_verified") is True:
        required_documents = doc.get("required_documents") or required_documents
        application_timeline = doc.get("application_timeline") or application_timeline
    elif (
        required_documents["status"] == "fetch_failed"
        and (doc.get("required_documents") or {}).get("status") == "available"
    ):
        required_documents = doc["required_documents"]

    update_fields = {
        "required_documents": required_documents,
        "application_timeline": application_timeline,
    }
    if object_id:
        update_fields["myscheme_object_id"] = object_id
    if open_date_raw:
        update_fields["scheme_open_date_raw"] = open_date_raw
    if close_date_raw:
        update_fields["scheme_close_date_raw"] = close_date_raw

    status = required_documents["status"]
    if status == "available":
        stats["documents_fetched"] += 1
    elif status == "fetch_failed":
        stats["documents_failed"] += 1
    else:
        stats["documents_missing"] += 1

    if not dry_run:
        await db["schemes"].update_one({"_id": doc["_id"]}, {"$set": update_fields})


async def create_indexes(db) -> None:
    await db["schemes"].create_index([("status", 1), ("myscheme_slug", 1)], name="ix_status_slug")
    await db["schemes"].create_index("myscheme_slug", name="ix_slug")
    await db["schemes"].create_index("myscheme_object_id", name="ix_object_id", sparse=True)
    await db["schemes"].create_index("scheme_id", name="ix_scheme_id")
    print("Indexes ensured: ix_status_slug, ix_slug, ix_object_id (sparse), ix_scheme_id")


async def run(args: argparse.Namespace) -> None:
    client_db = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client_db[settings.DATABASE_NAME]
    try:
        await db.command("ping")
    except Exception as e:
        print(f"ERROR: could not connect to MongoDB: {e}")
        return
    print(f"Connected to database: {settings.DATABASE_NAME}")

    query: Dict[str, Any] = {}
    if args.slug:
        query = {"myscheme_slug": {"$in": args.slug}}
    else:
        query = selection_query(args.force)

    cursor = db["schemes"].find(query)
    if args.limit:
        cursor = cursor.limit(args.limit)

    schemes = await cursor.to_list(length=None)
    print(f"Selected {len(schemes)} scheme(s) needing enrichment"
          f"{' (forced)' if args.force else ''}"
          f"{' [dry-run]' if args.dry_run else ''}")

    stats = {
        "documents_fetched": 0, "documents_missing": 0,
        "documents_failed": 0, "no_source": 0,
    }

    fetcher = MySchemeApiFetcher()
    sem = asyncio.Semaphore(args.concurrency)
    processed = 0

    async def process_with_limit(client, doc):
        nonlocal processed
        async with sem:
            try:
                await _process_one(
                    db, doc, fetcher, client,
                    offline=args.offline, dry_run=args.dry_run, stats=stats,
                )
            except Exception as e:
                print(f"  ERROR processing '{doc.get('myscheme_slug')}': {e}")
            finally:
                processed += 1
                if processed % 100 == 0 or processed == len(schemes):
                    print(f"  {processed}/{len(schemes)} schemes processed")

    if args.offline:
        for doc in schemes:
            await process_with_limit(None, doc)
    else:
        async with httpx.AsyncClient(headers=fetcher._build_headers(), timeout=20.0) as client:
            tasks = [process_with_limit(client, doc) for doc in schemes]
            await asyncio.gather(*tasks)

    print(
        f"Backfill complete: {stats['documents_fetched']} available, "
        f"{stats['documents_missing']} missing/unavailable, "
        f"{stats['documents_failed']} failed, {stats['no_source']} not-from-myscheme"
    )

    if not args.dry_run and schemes:
        try:
            await db["scheme_ingestion_log"].insert_one({
                "source": "myscheme.gov.in",
                "type": "enrichment_backfill",
                "selected": len(schemes),
                "documents_fetched": stats["documents_fetched"],
                "documents_missing": stats["documents_missing"],
                "documents_failed": stats["documents_failed"],
                "no_source": stats["no_source"],
                "forced": args.force,
                "offline": args.offline,
                "scraped_at": datetime.utcnow(),
            })
        except Exception as e:
            print(f"Could not write backfill log entry: {e}")

    if not args.dry_run:
        await create_indexes(db)

    client_db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill required_documents/application_timeline enrichment.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N schemes.")
    parser.add_argument("--slug", action="append", default=None, help="Process exactly this scheme (repeatable).")
    parser.add_argument("--dry-run", action="store_true", help="Compute and report, write nothing.")
    parser.add_argument("--force", action="store_true", help="Re-enrich even already-available schemes.")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent HTTP fetches (default 2).")
    parser.add_argument("--offline", action="store_true", help="No HTTP calls; derive timeline from stored fields only.")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
