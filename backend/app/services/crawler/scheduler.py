"""
Scheme Crawler Scheduler & Ingestion Orchestrator
---------------------------------------------------
Runs the full myScheme.gov.in ingestion pipeline:
  Fetcher → Parser → Normalizer → MongoDB (schemes + scheme_ingestion_log)

Features:
  - Incremental: only re-fetches details for new or stale schemes (>24h)
  - Resilient: catches per-scheme errors, continues with remaining
  - Logs every run to scheme_ingestion_log for audit trail
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.services.crawler.fetcher import MySchemeApiFetcher
from app.services.crawler.parser import MySchemeParser
from app.services.crawler.normalizer import MySchemeNormalizer
from app.services.crawler.rule_extractor import extract_rules_from_text
from app.core.database import get_db

logger = logging.getLogger(__name__)

# Schemes older than this are considered stale and re-fetched
STALE_THRESHOLD_HOURS = 24


class MySchemeIngestionScheduler:
    """Orchestrates fetch → parse → normalize → database pipeline for myScheme.gov.in."""

    def __init__(self):
        self.fetcher = MySchemeApiFetcher()
        self.parser = MySchemeParser()
        self.normalizer = MySchemeNormalizer()

    async def run_ingestion_cycle(self, category_filter: Optional[str] = None,
                                   limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Full ingestion cycle:
        1. Fetch summaries from search endpoint
        2. Filter out schemes already fresh in DB
        3. Fetch details for new/stale schemes
        4. Normalize and upsert into MongoDB
        5. Log the run

        Returns summary dict with counts.
        """
        run_start = datetime.utcnow()
        stats = {
            "started_at": run_start,
            "category_filter": category_filter,
            "summaries_fetched": 0,
            "new_schemes": 0,
            "updated_schemes": 0,
            "skipped_fresh": 0,
            "errors": 0,
            "completed_at": None,
        }

        db = get_db()
        if db is None:
            logger.error("Database not available — skipping ingestion cycle")
            stats["errors"] = 1
            return stats

        # Step 1: Fetch all summaries
        logger.info(f"Starting myScheme ingestion cycle (category={category_filter})")
        try:
            summaries = await self.fetcher.fetch_all_summaries(
                category=category_filter, limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to fetch summaries: {e}")
            stats["errors"] = 1
            await self._log_run(db, stats)
            return stats

        stats["summaries_fetched"] = len(summaries)
        logger.info(f"Fetched {len(summaries)} scheme summaries from myScheme API")

        if not summaries:
            stats["completed_at"] = datetime.utcnow()
            await self._log_run(db, stats)
            return stats

        # Step 2: Determine which schemes need detail fetching (new or stale)
        stale_cutoff = datetime.utcnow() - timedelta(hours=STALE_THRESHOLD_HOURS)
        slugs_to_fetch = []
        slug_to_summary = {}

        for summary_raw in summaries:
            parsed_summary = self.parser.parse_summary(summary_raw)
            slug = parsed_summary.get("slug")
            if not slug:
                continue
            slug_to_summary[slug] = parsed_summary

            # Check if we already have a fresh copy in DB
            existing = await db["schemes"].find_one(
                {"myscheme_slug": slug},
                {"last_fetched": 1, "content_hash": 1}
            )

            if existing and existing.get("last_fetched"):
                last_fetched = existing["last_fetched"]
                if isinstance(last_fetched, datetime) and last_fetched > stale_cutoff:
                    stats["skipped_fresh"] += 1
                    continue

            slugs_to_fetch.append(slug)

        logger.info(
            f"Need to fetch details for {len(slugs_to_fetch)} schemes "
            f"({stats['skipped_fresh']} skipped as fresh)"
        )

        # Step 3: Fetch details for new/stale schemes
        if slugs_to_fetch:
            details = await self.fetcher.fetch_details_batch(slugs_to_fetch)
        else:
            details = {}

        # Step 4: Normalize, extract rules, and upsert concurrently
        sem = asyncio.Semaphore(10)
        processed_count = 0

        async def process_one_scheme(slug: str):
            nonlocal processed_count
            async with sem:
                try:
                    parsed_summary = slug_to_summary[slug]
                    detail_payload = details.get(slug)

                    merged = self.parser.merge_summary_and_detail(parsed_summary, detail_payload)
                    normalized = self.normalizer.normalize(merged)

                    # Extract rules and benefit_calculation using Gemini LLM / heuristic parser
                    if normalized.get("eligibility_raw") or normalized.get("benefits_raw"):
                        try:
                            llm_result = await extract_rules_from_text(
                                scheme_name=normalized["name"],
                                eligibility_text=normalized.get("eligibility_raw", ""),
                                benefits_text=normalized.get("benefits_raw", "")
                            )
                            if llm_result.get("rules"):
                                normalized["rules"] = llm_result["rules"]
                            if llm_result.get("benefit_calculation"):
                                normalized["benefit_calculation"] = llm_result["benefit_calculation"]
                            normalized["extraction_method"] = llm_result.get("extraction_method", "fallback")
                        except Exception as llm_err:
                            logger.warning(f"Rule extraction warning for '{slug}': {llm_err}")

                    # Upsert by myscheme_slug or scheme_id (prevents duplicate seed records)
                    existing = await db["schemes"].find_one({
                        "$or": [
                            {"myscheme_slug": slug},
                            {"scheme_id": normalized.get("scheme_id")}
                        ]
                    })

                    # ── Ingestion-time state rule injection ─────────────────────────────
                    # If the scheme targets a specific state but the LLM/heuristic
                    # extractor failed to produce an explicit state rule, inject it here
                    # so the DB document is self-consistent. This is cheaper than
                    # deriving it on every evaluation request.
                    scheme_state_val = normalized.get("state")
                    if scheme_state_val and str(scheme_state_val).lower() not in [
                        "", "all states", "national", "india", "central", "all"
                    ]:
                        existing_rules = normalized.get("rules") or []
                        if not any(r.get("field") == "state" for r in existing_rules):
                            normalized["rules"] = existing_rules + [
                                {"field": "state", "operator": "==", "value": scheme_state_val}
                            ]
                            logger.debug(f"Injected implicit state rule for '{slug}': {scheme_state_val}")
                            
                    # ── Ingestion-time gender rule injection ────────────────────────────
                    # Implicit gender rule from eligibility_raw
                    elig_raw = str(normalized.get("eligibility_raw", "")).lower()
                    existing_rules = normalized.get("rules") or []
                    if not any(r.get("field") == "gender" for r in existing_rules):
                        if "women only" in elig_raw or "female" in elig_raw or "women" in elig_raw or "girl" in elig_raw:
                            if "male and female" not in elig_raw and "men and women" not in elig_raw:
                                normalized["rules"] = existing_rules + [
                                    {"field": "gender", "operator": "==", "value": "female"}
                                ]
                                logger.debug(f"Injected implicit gender rule for '{slug}'")

                    # ── Manual-verification & rule protection ─────────────────────────
                    # Priority 1 (strongest): manually_verified=True in DB → never overwrite
                    #   rules or benefit_calculation regardless of what the LLM extracted.
                    # Priority 2: published scheme with valid rules → preserve existing rules
                    #   unless force_reextract flag is set on the incoming document.
                    if existing:
                        if existing.get("manually_verified") is True:
                            # Hard lock — ingestion must not touch hand-patched fields
                            normalized["rules"] = existing["rules"]
                            normalized["benefit_calculation"] = existing.get(
                                "benefit_calculation", normalized.get("benefit_calculation")
                            )
                            normalized["status"] = existing.get("status", normalized["status"])
                            normalized["state"] = existing.get("state", normalized.get("state"))
                            normalized["category"] = existing.get("category", normalized.get("category"))
                            logger.debug(f"Preserving manually_verified rules and metadata for '{slug}'")
                        elif (
                            existing.get("status") == "published"
                            and existing.get("rules")
                            and len(existing["rules"]) > 0
                            and not normalized.get("force_reextract", False)
                        ):
                            normalized["rules"] = existing["rules"]
                            if existing.get("benefit_calculation"):
                                normalized["benefit_calculation"] = existing["benefit_calculation"]
                            normalized["status"] = "published"

                    # Set status as published if rules exist; pending_review if no rules extracted
                    if normalized.get("rules") and len(normalized["rules"]) > 0:
                        normalized["status"] = "published"
                    else:
                        normalized["status"] = "pending_review"

                    if existing:
                        # Diff old vs new document for meaningful changes
                        changed_fields = []
                        if existing.get("eligibility_raw") != normalized.get("eligibility_raw"):
                            changed_fields.append("eligibility")
                        if existing.get("benefits_raw") != normalized.get("benefits_raw") or existing.get("benefit_calculation") != normalized.get("benefit_calculation"):
                            changed_fields.append("benefits")
                        if existing.get("status") != normalized.get("status"):
                            changed_fields.append("status")
                        if existing.get("rules") != normalized.get("rules"):
                            changed_fields.append("rules")

                        update_fields = {
                            "name": normalized["name"],
                            "department": normalized["department"],
                            "description": normalized["description"],
                            "category": normalized["category"],
                            "level": normalized["level"],
                            "state": normalized["state"],
                            "benefit_type": normalized["benefit_type"],
                            "source_url": normalized["source_url"],
                            "myscheme_slug": slug,
                            "myscheme_tags": normalized["myscheme_tags"],
                            "eligibility_raw": normalized["eligibility_raw"],
                            "benefits_raw": normalized["benefits_raw"],
                            "rules": normalized["rules"],
                            "benefit_calculation": normalized["benefit_calculation"],
                            "last_fetched": normalized["last_fetched"],
                            "content_hash": normalized["content_hash"],
                            "updated_at": datetime.utcnow(),
                            "status": normalized["status"],
                            # Preserve manually_verified flag — never clear it via ingestion
                            **(  # Only include if it already exists to avoid writing None
                                {"manually_verified": existing.get("manually_verified")}
                                if existing.get("manually_verified") is not None else {}
                            ),
                        }
                        await db["schemes"].update_one(
                            {"_id": existing["_id"]},
                            {"$set": update_fields}
                        )
                        stats["updated_schemes"] += 1

                        # Generate change event and notify linked farmers if meaningful fields changed
                        if changed_fields:
                            try:
                                change_event = {
                                    "scheme_id": normalized["scheme_id"],
                                    "myscheme_slug": slug,
                                    "scheme_name": normalized["name"],
                                    "changed_fields": changed_fields,
                                    "timestamp": datetime.utcnow()
                                }
                                await db["scheme_change_events"].insert_one(change_event)

                                # Find all farmers who viewed or applied to this scheme
                                app_cursor = db["applications"].find({
                                    "$or": [
                                        {"scheme_id": normalized["scheme_id"]},
                                        {"myscheme_slug": slug}
                                    ]
                                })
                                affected_farmer_ids = set()
                                async for app_doc in app_cursor:
                                    if app_doc.get("farmer_id"):
                                        affected_farmer_ids.add(str(app_doc["farmer_id"]))

                                for f_id in affected_farmer_ids:
                                    notification_doc = {
                                        "farmer_id": f_id,
                                        "scheme_id": normalized["scheme_id"],
                                        "myscheme_slug": slug,
                                        "scheme_name": normalized["name"],
                                        "title": f"Scheme Updated: {normalized['name']}",
                                        "message": f"The {', '.join(changed_fields)} for scheme '{normalized['name']}' have been updated.",
                                        "change_type": "scheme_update",
                                        "changed_fields": changed_fields,
                                        "read": False,
                                        "created_at": datetime.utcnow()
                                    }
                                    await db["notifications"].insert_one(notification_doc)
                            except Exception as notif_err:
                                logger.warning(f"Error creating change notifications for '{slug}': {notif_err}")

                    else:
                        normalized["created_at"] = datetime.utcnow()
                        await db["schemes"].insert_one(normalized)
                        stats["new_schemes"] += 1

                except Exception as e:
                    logger.error(f"Error processing scheme slug '{slug}': {e}")
                    stats["errors"] += 1
                finally:
                    processed_count += 1
                    if processed_count % 100 == 0 or processed_count == len(slugs_to_fetch):
                        logger.info(f"  {processed_count}/{len(slugs_to_fetch)} schemes processed and saved to DB")

        if slugs_to_fetch:
            tasks = [process_one_scheme(slug) for slug in slugs_to_fetch]
            await asyncio.gather(*tasks)

        stats["completed_at"] = datetime.utcnow()
        await self._log_run(db, stats)

        logger.info(
            f"Ingestion cycle complete: "
            f"{stats['new_schemes']} new, {stats['updated_schemes']} updated, "
            f"{stats['skipped_fresh']} skipped, {stats['errors']} errors"
        )
        return stats

    async def _log_run(self, db, stats: Dict[str, Any]):
        """Write a run summary to scheme_ingestion_log for audit."""
        try:
            log_entry = {
                "source": "myscheme.gov.in",
                "type": "ingestion_run",
                "category_filter": stats.get("category_filter"),
                "summaries_fetched": stats.get("summaries_fetched", 0),
                "new_schemes": stats.get("new_schemes", 0),
                "updated_schemes": stats.get("updated_schemes", 0),
                "skipped_fresh": stats.get("skipped_fresh", 0),
                "errors": stats.get("errors", 0),
                "started_at": stats.get("started_at"),
                "completed_at": stats.get("completed_at"),
                "scraped_at": datetime.utcnow(),
            }
            await db["scheme_ingestion_log"].insert_one(log_entry)
        except Exception as e:
            logger.warning(f"Could not write ingestion log: {e}")


# --- Background daily task (started from main.py lifespan) ---

async def run_daily_ingestion_loop():
    """
    Background coroutine that runs ingestion once on startup, then daily.
    Designed to be started via asyncio.create_task() in the FastAPI lifespan.
    """
    scheduler = MySchemeIngestionScheduler()

    # Initial run with a short delay to let the app fully start
    await asyncio.sleep(5)
    logger.info("Running initial full myScheme ingestion cycle (all categories & states)...")
    try:
        await scheduler.run_ingestion_cycle(category_filter=None, limit=None)
    except Exception as e:
        logger.error(f"Initial ingestion cycle failed: {e}")

    # Daily loop — unrestricted full catalog refresh
    while True:
        await asyncio.sleep(86400)  # 24 hours
        logger.info("Running scheduled daily full myScheme ingestion cycle...")
        try:
            await scheduler.run_ingestion_cycle(category_filter=None, limit=None)
        except Exception as e:
            logger.error(f"Daily ingestion cycle failed: {e}")
