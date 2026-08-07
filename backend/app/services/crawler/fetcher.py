"""
myScheme.gov.in API Fetcher
----------------------------
Async httpx client for the undocumented myScheme frontend API.
Adapted from the standalone myscheme_ingest.py script into the
project's async FastAPI conventions.

Endpoints used (reverse-engineered from myscheme.gov.in DevTools):
  - Search:  GET /search/v6/schemes
  - Detail:  GET /schemes/v6/public/schemes
  - Facets:  GET /search/v6/schemes/facets
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Constants (from reference script) ---
PAGE_SIZE = 100
REQUEST_DELAY_SEC = 0.4  # be polite — undocumented endpoint, no published rate limit
MAX_RETRIES = 5
RETRY_BACKOFF_FACTOR = 1.5
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# Browser-like headers matching those observed in DevTools
_BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}


class MySchemeApiFetcher:
    """Async fetcher for the myScheme.gov.in internal JSON API."""

    def __init__(self):
        self.base_url = settings.MYSCHEME_API_BASE.rstrip("/")
        self.api_key = settings.MYSCHEME_API_KEY
        if not self.api_key:
            logger.warning("MYSCHEME_API_KEY is not set — myScheme API calls will fail")

    def _build_headers(self) -> Dict[str, str]:
        headers = dict(_BASE_HEADERS)
        headers["X-Api-Key"] = self.api_key
        return headers

    async def _request_with_retry(self, client: httpx.AsyncClient,
                                   url: str, params: Dict[str, Any]) -> Optional[httpx.Response]:
        """GET request with exponential backoff retry on transient errors."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.get(url, params=params, timeout=20.0)
                if resp.status_code in RETRY_STATUS_CODES:
                    wait = 10.0 * attempt if resp.status_code == 429 else RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(
                        f"Retryable status {resp.status_code} from {url} "
                        f"(attempt {attempt}/{MAX_RETRIES}), waiting {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)
                    continue
                return resp
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
                wait = RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(
                    f"Request error {exc.__class__.__name__} for {url} "
                    f"(attempt {attempt}/{MAX_RETRIES}), waiting {wait:.1f}s"
                )
                await asyncio.sleep(wait)
        logger.error(f"All {MAX_RETRIES} retries exhausted for {url}")
        return None

    async def fetch_facets(self) -> Optional[Dict]:
        """Fetch the full filter taxonomy (states, categories, occupation, caste, etc.)."""
        url = f"{self.base_url}/search/v6/schemes/facets"
        async with httpx.AsyncClient(headers=self._build_headers()) as client:
            resp = await self._request_with_retry(client, url, {"lang": "en"})
            if resp and resp.status_code == 200:
                return resp.json()
            return None

    async def fetch_search_page(self, client: httpx.AsyncClient,
                                 from_: int, size: int,
                                 category: Optional[str] = None) -> Optional[Dict]:
        """Fetch one page of scheme search results."""
        url = f"{self.base_url}/search/v6/schemes"
        params: Dict[str, Any] = {
            "lang": "en", "q": "", "sort": "",
            "from": from_, "size": size,
        }
        if category:
            params["schemeCategory"] = category

        resp = await self._request_with_retry(client, url, params)
        if resp and resp.status_code == 200:
            return resp.json()
        return None

    async def fetch_all_summaries(self, category: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[Dict]:
        """
        Page through the search endpoint and collect all scheme summary records.
        Adapted from reference script's fetch_all_summaries().
        """
        summaries: List[Dict] = []
        from_ = 0
        total = None

        async with httpx.AsyncClient(headers=self._build_headers()) as client:
            while True:
                page = await self.fetch_search_page(client, from_, PAGE_SIZE, category=category)
                if page is None:
                    logger.error("Search page returned None — aborting pagination")
                    break

                data = page.get("data", {})
                if total is None:
                    total = data.get("summary", {}).get("total", 0)
                    logger.info(f"myScheme search: {total} total schemes matching query")

                items = data.get("hits", {}).get("items", [])
                if not items:
                    break

                for item in items:
                    fields = item.get("fields", {})
                    fields["_id"] = item.get("id")
                    summaries.append(fields)

                from_ += PAGE_SIZE
                logger.info(f"  fetched {len(summaries)}/{total} summaries")

                if limit and len(summaries) >= limit:
                    summaries = summaries[:limit]
                    break
                if from_ >= total:
                    break

                await asyncio.sleep(REQUEST_DELAY_SEC)

        return summaries

    async def fetch_scheme_detail(self, client: httpx.AsyncClient,
                                   slug: str) -> Optional[Dict]:
        """Fetch full detail JSON for one scheme by slug."""
        url = f"{self.base_url}/schemes/v6/public/schemes"
        resp = await self._request_with_retry(client, url, {"slug": slug, "lang": "en"})

        if resp is None or resp.status_code != 200:
            logger.warning(f"Failed to fetch detail for slug '{slug}': "
                           f"status={resp.status_code if resp else 'no response'}")
            return None

        payload = resp.json()
        if payload.get("status") != "Success":
            logger.warning(f"Non-success response for slug '{slug}': "
                           f"{payload.get('errorDescription')}")
            return None

        return payload

    async def fetch_details_batch(self, slugs: List[str], max_concurrency: int = 2) -> Dict[str, Optional[Dict]]:
        """Fetch details for a batch of slugs concurrently with polite rate limiting."""
        results: Dict[str, Optional[Dict]] = {}
        sem = asyncio.Semaphore(max_concurrency)
        completed_count = 0

        async with httpx.AsyncClient(headers=self._build_headers(), timeout=20.0) as client:
            async def fetch_one(slug: str):
                nonlocal completed_count
                async with sem:
                    res = await self.fetch_scheme_detail(client, slug)
                    results[slug] = res
                    completed_count += 1
                    if completed_count % 50 == 0 or completed_count == len(slugs):
                        logger.info(f"  {completed_count}/{len(slugs)} scheme details fetched")
                    await asyncio.sleep(0.5)

            tasks = [fetch_one(slug) for slug in slugs]
            await asyncio.gather(*tasks)

        return results

