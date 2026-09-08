"""
Shared pytest fixtures for the scheme requirements/timeline/reasoning feature.

Fixture payloads are verbatim captures from the live myScheme.gov.in API,
taken 2026-09-08 (see docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md Part II).
Loaded from tests/fixtures/*.json rather than inlined so the verbatim JSON
is diff-able and reusable across test modules.
"""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load(name: str):
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_detail_payload():
    """Verbatim GET /schemes/v6/public/schemes?slug=pm-kisan&lang=en response."""
    return _load("pmkisan_detail.json")


@pytest.fixture
def sample_documents_payload():
    """Verbatim GET /schemes/v6/public/schemes/{id}/documents response for pm-kisan.
    Has both documentsRequired_md and the documents_required AST."""
    return _load("pmkisan_documents.json")


@pytest.fixture
def sample_documents_payload_ast_only():
    """Same as sample_documents_payload but with documentsRequired_md removed —
    exercises the AST-only parsing path."""
    return _load("pmkisan_documents_ast_only.json")


@pytest.fixture
def sample_documents_payload_empty():
    """Verbatim response shape when a scheme has no documents section:
    {"status": "Success", "data": null}."""
    return _load("pmkisan_documents_empty.json")


@pytest.fixture
def sample_documents_payload_runon():
    """Verbatim-shaped payload reproducing the malformed run-on markdown list
    and double list markers observed on gpt-hbocwwb during the live audit:
    '1. [Undertaking](url)1. [Work Slip](url)' with no separating newline,
    plus '(If applicable)' conditional phrasing."""
    return _load("gpt_hbocwwb_documents.json")


@pytest.fixture
def sample_search_item():
    """Verbatim search result item for 'sui' (Stand-Up India), which is one of
    only 5/1000 schemes carrying a schemeCloseDate."""
    return _load("sui_search_item.json")


# ---------------------------------------------------------------------------
# Minimal in-memory async Mongo double, used by ingestion/scheduler tests.
# Supports just the subset of the motor API the crawler scheduler calls:
# find_one (with a positive projection), find (async-iterable cursor),
# update_one ($set only), insert_one.
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs
        self._iter = None

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length=None):
        return list(self._docs) if length is None else list(self._docs)[:length]


def _fake_match(query, doc):
    if not query:
        return True
    for key, value in query.items():
        if key == "$or":
            if not any(_fake_match(sub, doc) for sub in value):
                return False
            continue
        if isinstance(value, dict):
            for op, opval in value.items():
                if op == "$exists":
                    if (key in doc) != opval:
                        return False
                elif op == "$ne":
                    if doc.get(key) == opval:
                        return False
                elif op == "$in":
                    if doc.get(key) not in opval:
                        return False
                else:
                    return False
        else:
            if doc.get(key) != value:
                return False
    return True


class _FakeCollection:
    def __init__(self):
        self.docs = []
        self._next_id = 1

    async def find_one(self, query=None, projection=None):
        for doc in self.docs:
            if _fake_match(query or {}, doc):
                if projection:
                    result = {k: doc.get(k) for k, v in projection.items() if v}
                    result["_id"] = doc.get("_id")
                    return result
                return dict(doc)
        return None

    def find(self, query=None):
        matched = [dict(d) for d in self.docs if _fake_match(query or {}, d)]
        return _FakeCursor(matched)

    async def update_one(self, query, update):
        for doc in self.docs:
            if _fake_match(query, doc):
                doc.update(update.get("$set", {}))
                return
        # Mongo semantics: matching nothing is a no-op unless upsert=True,
        # which the scheduler never passes for scheme updates.

    async def insert_one(self, doc):
        doc = dict(doc)
        if "_id" not in doc:
            doc["_id"] = f"fakeid{self._next_id}"
            self._next_id += 1
        self.docs.append(doc)
        return doc

    async def count_documents(self, query=None):
        return sum(1 for d in self.docs if _fake_match(query or {}, d))


class FakeDB:
    """Drop-in stand-in for the object app.core.database.get_db() returns."""

    def __init__(self):
        self._collections: dict = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = _FakeCollection()
        return self._collections[name]


@pytest.fixture
def fake_db():
    return FakeDB()
