# Implementation Plan — Scheme Requirements, Timeline & Evidence-Based Reasoning

**Status:** Design complete. Ready for implementation.
**Author:** Architecture pass (Opus 5), 2026-09-08
**Implementer:** Claude Sonnet 5
**Repository:** `C:\Users\gmore\OneDrive\Desktop\IPD_Project\ipd` (git root)

> Every file path, function name, field name, endpoint, and payload shape below was
> verified against the live repository, the live MongoDB (`agrisense_db`, 4,788
> scheme documents), and the live myScheme.gov.in API on 2026-09-08. Nothing here
> is assumed. Where a fact was measured, the measurement is quoted.

---

# PART I — WHAT THE SYSTEM ACTUALLY IS TODAY

## 1. Verified current architecture

### 1.1 Repository layout

```
ipd/                                  ← git root
├── CLAUDE.md
├── MASTER_PROJECT_DOCUMENTATION.md
├── README_PROJECT_ANALYSIS.md
├── memory-bank/                      ← knowledge base, written 2026-07-21, partly stale
├── backend/
│   ├── .env                          ← MONGO_URI, MYSCHEME_API_KEY, GEMINI_API_KEY, …
│   ├── requirements.txt              ← merge conflict noted in CLAUDE.md is ALREADY RESOLVED
│   ├── venv/                         ← Python 3.14 venv, no pytest installed
│   ├── scripts/seed_schemes.py
│   └── app/
│       ├── main.py                   ← lifespan: mongo connect → seed → ingestion task
│       ├── core/{config,database,security}.py
│       ├── models/{farmer,scheme,story}.py
│       ├── api/{auth,farmers,schemes,upload,stories,documents,monitoring}.py
│       ├── document_processing/      ← IDP (OCR + Gemini Vision) — NOT touched by this feature
│       ├── ml/
│       │   ├── rules/rules_engine.py
│       │   ├── explainability/scheme_explainer.py
│       │   ├── inference/{ranking_engine,success_predictor,benefit_predictor}.py
│       │   ├── graph/knowledge_graph.py
│       │   ├── features/feature_store.py
│       │   ├── preprocessing/{data_cleaning,feature_engineering}.py
│       │   ├── utils/profile_mapper.py
│       │   └── services/recommendation_service.py
│       └── services/crawler/
│           ├── fetcher.py            ← myScheme HTTP client
│           ├── parser.py             ← payload → intermediate dict
│           ├── normalizer.py         ← intermediate dict → Mongo scheme doc
│           ├── rule_extractor.py     ← Gemini/heuristic eligibility rule extraction
│           └── scheduler.py          ← orchestration + upsert + change events
└── frontend/                         ← React 19 + Vite + TS + Tailwind + shadcn/ui
    └── src/
        ├── lib/api.ts                ← single Axios instance, JWT interceptor
        ├── pages/Dashboard.tsx       ← 1,245 lines; ALL recommendation UI lives here
        ├── i18n/locales/{en,hi,mr,gu}.json
        └── components/ui/            ← badge, button, card, dialog, input, label,
                                         progress, select, separator, sonner, tabs
```

### 1.2 The real end-to-end flow (traced, not assumed)

```
myScheme.gov.in
  │
  │  GET https://api.myscheme.gov.in/search/v6/schemes?lang=en&q=&sort=&from=N&size=100
  │     → data.hits.items[] = { id: "<elasticsearch id>", fields: {...}, highlight: {} }
  ▼
backend/app/services/crawler/fetcher.py :: MySchemeApiFetcher.fetch_all_summaries()
  │     (sets fields["_id"] = item["id"]  ← this is the ES id, NOT the Mongo id)
  ▼
backend/app/services/crawler/parser.py :: MySchemeParser.parse_summary()
  │     → { myscheme_id, slug, scheme_name, short_title, level, ministry,
  │         categories, tags, beneficiary_states, brief_description, close_date }
  │
  │  GET https://api.myscheme.gov.in/schemes/v6/public/schemes?slug=<slug>&lang=en
  │     → data = { _id: "<MONGO ObjectId hex>", slug, en: {...} }
  ▼
backend/app/services/crawler/fetcher.py :: fetch_scheme_detail() / fetch_details_batch()
  ▼
backend/app/services/crawler/parser.py :: MySchemeParser.parse_detail()
  │     → { implementing_agency, scheme_type, scheme_open_date, target_beneficiaries,
  │         detailed_description_md, benefits_md, exclusions_md, benefit_type_label,
  │         eligibility_description_md, application_process }
  ▼
backend/app/services/crawler/parser.py :: merge_summary_and_detail()
  ▼
backend/app/services/crawler/normalizer.py :: MySchemeNormalizer.normalize()
  │     → the exact Mongo `schemes` document (see 1.3)
  ▼
backend/app/services/crawler/rule_extractor.py :: extract_rules_from_text()
  │     Gemini `gemini-2.0-flash` if GEMINI_API_KEY set, else regex heuristics
  │     → rules[] + benefit_calculation{}
  ▼
backend/app/services/crawler/scheduler.py :: MySchemeIngestionScheduler.run_ingestion_cycle()
  │     state-rule injection, gender-rule injection, manually_verified protection,
  │     status = published | pending_review, upsert, scheme_change_events, notifications
  ▼
MongoDB  agrisense_db.schemes   (4,788 docs, avgObjSize 2,402 B, size 11.5 MB)
  ▼
backend/app/api/farmers.py :: get_published_schemes(db)
  │     db["schemes"].find({"status":"published","rules":{"$exists":True,"$ne":[]}})
  │     → 4,774 full documents, no projection, NO INDEX (full collection scan)
  ▼
backend/app/ml/services/recommendation_service.py :: RecommendationService.get_recommendations()
  ▼
backend/app/ml/inference/ranking_engine.py :: SchemeRankingEngine.rank_schemes()
  │   1. FeatureStore.build_features()  → clean_farmer_profile + add_derived_features
  │   2. RulesEngine.filter_schemes()   → eligible[] / ineligible[], each carrying
  │                                        passed_rules[] and failed_rules[]
  │   3. SchemeExplainer.explain_eligible / explain_ineligible  → List[str]
  │   4. SchemeSuccessPredictor.predict_batch  → probabilities
  │   5. BenefitPredictor.predict_benefit      → predicted_financial_value
  │   6. affinity/proximity scoring            → relevance_score
  │   7. SchemeKnowledgeGraph.get_optimal_scheme_bundles()  → MWIS bundles
  │   8. SchemePolicy.select_scheme()
  ▼
backend/app/api/farmers.py :: GET /api/farmers/me   (response_model=FarmerResponse)
  ▼
frontend/src/pages/Dashboard.tsx  (tabs: eligible | ineligible | monitored | risk_alerts)
```

### 1.3 The actual Mongo `schemes` document (read from the live DB)

Verified key set across the collection:

```
_id, scheme_id, name, rules, conflicts_with, benefit_calculation, department,
description, category, level, state, benefit_type, status, source_url,
myscheme_slug, myscheme_tags, eligibility_raw, benefits_raw, last_fetched,
content_hash, updated_at, created_at, extraction_method, extraction_confidence,
financial_benefit, manually_verified
```

Real example (`sui` / Stand-Up India):

```json
{
  "scheme_id": "SUI",
  "name": "Stand-Up India",
  "rules": [
    {"field": "category", "operator": "==", "value": "SC"},
    {"field": "occupation_type", "operator": "==", "value": "business_owner"},
    {"field": "age", "operator": ">=", "value": 18}
  ],
  "conflicts_with": [],
  "benefit_calculation": {"type": "flat_rate", "base_rate": 0},
  "department": "Ministry Of Finance",
  "category": "Business & Entrepreneurship",
  "level": "central", "state": null,
  "status": "published",
  "source_url": "https://www.myscheme.gov.in/schemes/sui",
  "myscheme_slug": "sui",
  "eligibility_raw": "\n- Finance is  provided for Greenfield Enterprises.\n- If the applicant is a male, he must be from SC / ST category.\n…",
  "benefits_raw": "…",
  "last_fetched": "2026-09-07T16:24:22.874Z",
  "content_hash": "573e36a34be3…",
  "extraction_method": "heuristic",
  "extraction_confidence": "high",
  "manually_verified": true
}
```

### 1.4 Live measurements (2026-09-08)

| Measurement | Value |
|---|---|
| `schemes` documents | 4,788 |
| `status: published` | 4,774 |
| `published` **and** non-empty `rules` (the recommendation query) | 4,774 |
| `pending_review` | 14 |
| non-empty `eligibility_raw` | 4,775 |
| `manually_verified: true` | 147 |
| `extraction_method: "llm"` | **0** |
| `extraction_method: "heuristic"` | 4,732 |
| Indexes on `schemes` | **`_id_` only** — the recommendation query is a full collection scan |
| Duplicate `scheme_id` groups | 8 |
| Duplicate `myscheme_slug` groups | 9 (includes the `null` group from YAML seeding) |
| Distinct `myscheme_slug` | 4,771 |
| Last ingestion run | 2026-09-07, 4,772 summaries, 0 errors, **35 min wall time** |
| Live ranking for one real farmer | **19.0 s**; 114 eligible, **4,652 ineligible**, 1 bundle |
| `recommended_schemes` JSON | 96.8 KB |
| `ineligible_schemes` JSON | **1.43 MB** |
| `recommended_bundles` JSON | 97.1 KB (duplicates the eligible objects) |

### 1.5 Pre-existing defects found during this audit (do NOT fix unless listed)

| ID | File | Issue |
|---|---|---|
| PRE-1 | `backend/app/api/farmers.py` | `datetime` is used in `record_scheme_action`, `get_new_schemes_summary` etc. but **never imported**. Any call to `POST /api/farmers/me/applications` raises `NameError`. **You MUST fix this** — Phase 8 depends on the file importing `datetime`. |
| PRE-2 | `backend/app/api/farmers.py` | `ineligible_schemes` returns all 4,652 non-matching schemes (1.43 MB). **Do not make this worse.** Out of scope to fix. |
| PRE-3 | `backend/app/services/crawler/normalizer.py` | Silently drops `close_date`, `scheme_open_date`, `application_process`, and `myscheme_id` — all already parsed by `parser.py`. **This feature fixes that.** |
| PRE-4 | `backend/app/services/crawler/rule_extractor.py` | Heuristics produce demonstrably wrong rules. Verified examples: `post-st` ("Post Matric Scholarship for **Scheduled Tribe**") got `category == "SC"` and `gender == "female"`; `kbpyy` got `gender == "female"` from a *preference* sentence; `syss` got `occupation_type == "government_employee"` from "child of a Government employee". **Out of scope to fix, but this is the single biggest correctness risk for the reasoning feature — see §12.** |
| PRE-5 | `backend/app/models/farmer.py` | `SchemeRecommendation` / `IneligibleScheme` silently strip any field not declared on the model. Verified: `source_url`, `relevance_score`, `score_breakdown` are all produced by `ranking_engine.py` and all discarded by FastAPI's `response_model`. **Any new field you add MUST be declared on these models or it will vanish.** |
| PRE-6 | `backend/app/services/crawler/parser.py` | `parse_summary()` stores `item["id"]` as `myscheme_id`. That is the **Elasticsearch** id (e.g. `LBezF5gB5uF80_MGGY81`), *not* the Mongo ObjectId the sub-resource endpoints need. |

---

# PART II — DATA AVAILABILITY INVESTIGATION (Phase 3 answers)

All of the following was probed live against `api.myscheme.gov.in` on 2026-09-08.

## 2. What the source actually contains

### 2.1 The detail endpoint does NOT carry documents

`GET /schemes/v6/public/schemes?slug=pm-kisan&lang=en` returns exactly:

```
data._id                 "62a70e86f038bd8499a6aa53"   ← Mongo ObjectId (KEY DISCOVERY)
data.slug                "pm-kisan"
data.en.basicDetails     { dbtScheme, tags, schemeName, schemeShortTitle, level,
                           schemeType, schemeCategory, schemeSubCategory,
                           schemeOpenDate, targetBeneficiaries, schemeFor,
                           nodalMinistryName, nodalDepartmentName }
data.en.schemeContent    { references[], schemeImageUrl, detailedDescription_md,
                           benefits_md, exclusions_md, briefDescription,
                           detailedDescription, benefitTypes, benefits, exclusions }
data.en.applicationProcess [ { mode, url?, process[], process_md } ]
data.en.schemeDefinitions  [ { name, definition[], source, definitions_md } ]
data.en.eligibilityCriteria { eligibilityDescription_md, eligibilityDescription[] }
```

No `documentsRequired`. Verified by string search of the full payload.
`/schemes/v5/...` returns HTTP 500. `/schemes/v4/...` returns the same 5 keys.

### 2.2 The documents ARE available — on undiscovered sub-resource endpoints

Captured by hooking `XMLHttpRequest.open` in the live myscheme.gov.in SPA and
triggering a client-side route change. The site issues:

```
GET /schemes/v6/public/schemes/{mongoObjectId}/documents          ← REQUIRED DOCUMENTS
GET /schemes/v6/public/schemes/{mongoObjectId}/faqs
GET /schemes/v6/public/schemes/{mongoObjectId}/applicationchannel
GET /schemes/v6/public/schemes/{mongoObjectId}/news
```

`{mongoObjectId}` is `detail.data._id` — **not** the search result's `item.id`.
Same `X-Api-Key` / `Origin` / `Referer` headers as the existing calls.

Verified `documents` response for `pm-kisan`:

```json
{
  "status": "Success", "statusCode": 200,
  "data": {
    "_id": "62a7100ef038bd8499a6ac1c",
    "schemeId": "62a70e86f038bd8499a6aa53",
    "en": {
      "documents_required": [
        { "type": "ol_list", "children": [
            { "type": "list_item", "children": [ { "text": "Aadhaar Card." } ] },
            { "type": "list_item", "children": [ { "text": "Landholding papers." } ] },
            { "type": "list_item", "children": [ { "text": "Savings Bank Account." } ] }
        ]}
      ],
      "documentsRequired_md": "\n1. Aadhaar Card.\n1. Landholding papers.\n1. Savings Bank Account.\n\n<br>\n\n"
    }
  }
}
```

Additional verified shapes:

* **Unknown scheme id** → HTTP 200, `{"status":"Success", "data": null}`.
* **`documentsRequired_md` absent but `documents_required` AST present** — happens
  (e.g. `cmfccs`). You must read **both** and prefer whichever yields items.
* **`documentsRequired_md` present but AST yields 0 items** — also happens
  (e.g. `mfpffw`). Fall back to markdown list parsing.
* Text carries HTML entities (`&#39;`, `&amp;amp;#39;`) and inline markdown links,
  e.g. `1. [Undertaking](https://storage.hrylabour.gov.in/…)1. [Work Slip](…)`.
* Conditional phrasing is common and *verbatim* in the source:
  `"Caste Certificate (If applicable)"`, `"Income Certificate (for classes 9th to 10th)"`,
  `"Birth Certificate (If applicable)"`, `"Schedule Tribe Certificate for APST patients"`.

**Coverage (random samples):** 20/20 on one page, 9/15 on another → conservatively
**60–100 %, likely ≈ 85 %**. Design must handle "unavailable" as a first-class state.

### 2.3 Deadlines are almost entirely absent — this is the headline finding

| Source field | Where | Measured coverage |
|---|---|---|
| `schemeCloseDate` | search `item.fields` | **5 / 1,000 = 0.5 %** |
| `schemeOpenDate` | `detail.data.en.basicDetails` | **≈ 60 %** (9/15 sample) |
| Any structured application window | — | **does not exist** |
| Any recurring window | — | **does not exist** |
| Any state/category-specific deadline | — | **does not exist** |

Observed `schemeCloseDate` values: `sui → "2025-03-31"`, `ssieemaf → "2023-06-15"`
— i.e. the few that exist are already **in the past**. Format is a bare `YYYY-MM-DD`
with no timezone.

Free text mentions: only **42 / 4,788** `eligibility_raw` values and **5 / 4,788**
`benefits_raw` values match `last date|deadline|apply before|closing date`.

> **Design consequence:** For ~99 % of schemes the only honest answer is
> *"No closing date published on myScheme."* Any design that tries to synthesise a
> deadline is fabricating government information. **We will not parse dates out of
> free text.** Where free text mentions a deadline we surface a **verbatim excerpt**
> and link to the official page — never a parsed date.

### 2.4 Eligibility criteria: unstructured at source, structured only by us

* Source: `eligibilityCriteria.eligibilityDescription_md` — free-text markdown,
  HTML-escaped, mixing hard requirements with *preferences* ("preference will be
  given to…") and *definitions*.
* Stored verbatim as `eligibility_raw`.
* Structured `rules[]` are **derived by us** in `rule_extractor.py`, currently
  100 % heuristic (0 documents have `extraction_method: "llm"`, so the Gemini path
  is either unconfigured or failing silently in production).
* Nested/conditional structure exists in the *text* ("For CMHIS (EP): … For CMHIS (GC): …")
  but the rule model is a flat AND-list, so conditionality is lost.

### 2.5 Answers to Phase 3, A–K

| | Question | Answer |
|---|---|---|
| A | Documents already present? | **No** in the ingested payload; **yes** at source on an endpoint we do not call. |
| B | Deadlines already present? | `close_date` is *parsed* by `parser.py` and *dropped* by `normalizer.py`. `scheme_open_date` likewise. Source coverage: 0.5 % / 60 %. |
| C | Eligibility present? | Yes, verbatim in `eligibility_raw`. |
| D | Structured or unstructured? | Unstructured at source; structured `rules[]` derived by us, heuristically, with known errors. |
| E | Additional fields/endpoints? | Yes — `/documents`, `/faqs`, `/applicationchannel`, `/news` sub-resources keyed by `detail.data._id`. |
| F | Nested / HTML / rich text? | Yes: Slate-style AST (`type`/`children`/`text`), markdown mirrors (`*_md`), double-escaped HTML entities, inline markdown links. |
| G | Conditional? | Yes — but expressed only as *English text inside the document label* (`"(If applicable)"`, `"for APST patients"`). No machine-readable conditionality anywhere. |
| H | What happens when missing? | Today: nothing exists to be missing. New behaviour is specified in §14. |
| I | Re-ingestion? | Daily loop in `scheduler.py::run_daily_ingestion_loop` (startup + every 86,400 s). Per-scheme skip when `last_fetched` is < 24 h old. |
| J | Change detection? | `content_hash` = SHA-256 of `name + description + eligibility_raw` (computed but **never actually compared** — it is written, never read). Real detection is a field-by-field diff in `scheduler.py` producing `scheme_change_events` + `notifications`. |
| K | Staying in sync? | Enrichment must run **inside** the same per-scheme upsert transaction-equivalent so it can never drift from `last_fetched`, plus a standalone backfill script for the existing 4,788 rows. |

---

# PART III — THE DESIGN

## 3. Layer separation and provenance

```
SOURCE DATA          myScheme JSON: documentsRequired_md, documents_required AST,
                     schemeOpenDate, schemeCloseDate, applicationProcess[].mode/url
      │              → stored VERBATIM, never rewritten
      ▼
NORMALIZATION        HTML-unescape, markdown-link extraction, AST flattening,
                     ISO-8601 date parsing
      │              → produces `raw_text` (verbatim-equivalent) + parsed dates
      ▼
DERIVED / ENRICHED   document type classification via a closed alias vocabulary,
                     mandatory/conditional classification, timeline status
      │              → ALWAYS carries `doc_type: "UNKNOWN"` when unmatched
      ▼
ELIGIBILITY EVIDENCE RulesEngine passed_rules[] / failed_rules[]
      │              (already exists — currently thrown away after a string is built)
      ▼
RECOMMENDATION       ranking_engine relevance_score + MWIS bundles (unchanged)
      │
      ▼
EXPLANATION          deterministic MatchSignal[] → reason_summary sentence
      │              NO LLM. NO free generation.
      ▼
USER PRESENTATION    Dashboard.tsx cards
```

**Provenance contract.** Every user-facing factual claim must be traceable:

| Field shown to user | Provenance value | Meaning |
|---|---|---|
| document label | `raw_text` + `source: "myscheme_documents_api"` | verbatim from the government portal |
| document type icon/group | `doc_type` + `match_confidence` | derived by us; never shown as text |
| open/close date | `source: "myscheme_basic_details"` / `"myscheme_search_summary"` | verbatim date string preserved in `*_raw` |
| deadline excerpt | `source: "scheme_text_excerpt"` | verbatim substring of `eligibility_raw` |
| recommendation reason | `evidence_source: "scheme_rule"` + `rule_provenance` | which extraction produced the rule |

## 4. Architecture decision (Phase 5)

**Chosen: Hybrid — extend the existing ingestion pipeline with a dedicated,
idempotent enrichment stage, plus a standalone backfill script that reuses the
exact same stage.**

Rejected alternatives and why:

| Option | Verdict | Reason |
|---|---|---|
| 1. Extend parser only | Insufficient | Documents live on a *different HTTP endpoint*, so `fetcher.py` must change too; and normalization of document text is substantial enough to deserve its own module. |
| 2. Add a normalization layer only | Insufficient | Same reason. |
| 3. Dedicated enrichment stage | **Adopted** | Matches the existing `fetcher → parser → normalizer → rule_extractor → scheduler` decomposition exactly. |
| 4. Post-ingestion worker | **Adopted for backfill only** | A permanent second worker would duplicate the scheduler's semaphore/retry/logging machinery and could race the daily loop, producing conflicting writes. As a one-shot backfill script it is exactly right. |
| 5. Separate metadata service/collection | Rejected | The ranking hot path already loads all published schemes in one `find()`. A second collection needs a `$lookup` or an N+1 fetch on a path that already costs 19 s. Also creates a second source of truth for the same scheme. |
| 6. Fetch documents at recommendation time | Rejected outright | 114 eligible schemes × 1 HTTP call per request, against an undocumented government API with no published rate limit. |

**Storage decision: embed in the `schemes` document.** 1:1 cardinality, always read
together, Mongo is schemaless, and the crawler already embeds `eligibility_raw` /
`benefits_raw` by the same logic. Measured cost: ≈ 1.5–2 KB/scheme → collection
grows 11.5 MB → ≈ 20 MB. This is offset by the projection introduced in Phase 9.

**Idempotency.** Enrichment is a pure function of `(documents payload, basicDetails,
search fields)`. Re-running it produces byte-identical output. Keyed on
`myscheme_slug` (not `scheme_id` — 8 duplicate `scheme_id` groups exist). Writes are
`$set` on named sub-documents, never `$push`, so re-running can never duplicate.

## 5. Data model (Phase 6, 7, 9)

### 5.1 `schemes.required_documents` — new embedded sub-document

```json
{
  "status": "available",
  "source": "myscheme_documents_api",
  "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
  "fetched_at": "2026-09-08T09:14:22.101Z",
  "raw_markdown": "\n1. Aadhaar Card.\n1. Landholding papers.\n1. Savings Bank Account.\n\n<br>\n\n",
  "items": [
    {
      "raw_text": "Aadhaar Card.",
      "display_name": "Aadhaar Card",
      "doc_type": "AADHAAR",
      "requirement": "mandatory",
      "condition_text": null,
      "match_confidence": "high",
      "links": []
    },
    {
      "raw_text": "Caste Certificate (If applicable)",
      "display_name": "Caste Certificate",
      "doc_type": "CASTE_CERTIFICATE",
      "requirement": "conditional",
      "condition_text": "If applicable",
      "match_confidence": "high",
      "links": []
    },
    {
      "raw_text": "Undertaking",
      "display_name": "Undertaking",
      "doc_type": "UNKNOWN",
      "requirement": "mandatory",
      "condition_text": null,
      "match_confidence": "none",
      "links": ["https://storage.hrylabour.gov.in/uploads_new_2/bocw/scheme_undertaking/1628746916.pdf"]
    }
  ],
  "item_count": 3,
  "unmatched_count": 1,
  "extractor_version": 1
}
```

Field specification:

| Field | Type | Null? | Default | Source | Lifecycle |
|---|---|---|---|---|---|
| `status` | `str` enum `available` \| `unavailable` \| `fetch_failed` \| `not_fetched` | no | `"not_fetched"` | derived | overwritten each enrichment run |
| `source` | `str` | no | `"myscheme_documents_api"` | constant | — |
| `source_url` | `str` \| null | yes | scheme `source_url` | derived from slug | — |
| `fetched_at` | `datetime` (UTC) | yes | `null` | set at fetch | overwritten |
| `raw_markdown` | `str` \| null | yes | `null` | **verbatim source** | overwritten |
| `items[]` | `list[dict]` | no | `[]` | normalized | fully replaced, never appended |
| `items[].raw_text` | `str` | no | — | **verbatim source** (HTML-unescaped, links stripped to `links[]`) | — |
| `items[].display_name` | `str` | no | `= raw_text` when unmatched | derived | — |
| `items[].doc_type` | `str` enum (see §5.3) or `"UNKNOWN"` | no | `"UNKNOWN"` | derived | — |
| `items[].requirement` | `str` enum `mandatory` \| `conditional` \| `unknown` | no | `"mandatory"` | derived | — |
| `items[].condition_text` | `str` \| null | yes | `null` | **verbatim substring** | — |
| `items[].match_confidence` | `str` enum `high` \| `low` \| `none` | no | `"none"` | derived | — |
| `items[].links` | `list[str]` | no | `[]` | verbatim markdown link targets | — |
| `item_count` | `int` | no | `0` | derived | — |
| `unmatched_count` | `int` | no | `0` | derived | — |
| `extractor_version` | `int` | no | `1` | constant | bump when taxonomy changes → triggers re-derivation in backfill |

### 5.2 `schemes.application_timeline` — new embedded sub-document

```json
{
  "status": "window",
  "open_date": "2019-02-24T00:00:00Z",
  "close_date": "2025-03-31T00:00:00Z",
  "open_date_raw": "2019-02-24",
  "close_date_raw": "2025-03-31",
  "open_date_source": "myscheme_basic_details.schemeOpenDate",
  "close_date_source": "myscheme_search_summary.schemeCloseDate",
  "application_modes": [
    { "mode": "Online", "url": "https://pmkisan.gov.in/RegistrationFormnew.aspx" },
    { "mode": "Online - via CSC", "url": null }
  ],
  "text_mentions": [
    { "kind": "deadline_phrase", "excerpt": "…applications must be submitted before the last date notified…", "field": "eligibility_raw" }
  ],
  "fetched_at": "2026-09-08T09:14:22.101Z",
  "extractor_version": 1
}
```

| Field | Type | Null? | Default | Rules |
|---|---|---|---|---|
| `status` | enum `window` \| `open_ended` \| `unknown` | no | `"unknown"` | `window` iff `close_date` parsed; `open_ended` iff `open_date` parsed and no `close_date`; else `unknown`. **Never store `expired`/`closed`** — that is computed at read time so it cannot go stale. |
| `open_date` / `close_date` | `datetime` UTC-midnight \| null | yes | `null` | Only set when the raw string matches `^\d{4}-\d{2}-\d{2}$` **and** `datetime.strptime` succeeds. Anything else → `null` + a `text_mentions` entry of kind `unparseable_date`. |
| `open_date_raw` / `close_date_raw` | `str` \| null | yes | `null` | **verbatim** source string, always preserved even when parsing fails |
| `*_source` | `str` \| null | yes | `null` | provenance path |
| `application_modes[]` | list | no | `[]` | from `applicationProcess[].mode` / `.url`. Verbatim. |
| `text_mentions[]` | list | no | `[]` | **verbatim excerpts only** — see §5.5 |
| `extractor_version` | int | no | `1` | — |

**Timezone rule (mandatory).** myScheme emits bare calendar dates with no timezone.
Store them as UTC midnight. Expiry is evaluated against the **Asia/Kolkata calendar
date**: a scheme with `close_date = 2026-09-08` is *open* for the whole of
2026-09-08 IST and *expired* from 2026-09-09 IST onward. Implement with
`datetime.now(ZoneInfo("Asia/Kolkata")).date()` (stdlib `zoneinfo`; on Windows this
requires `tzdata`, which is already a transitive dependency of the installed
`pandas`/`tzlocal` — verify at import and fall back to a fixed `UTC+05:30` offset).

**Conflicting dates.** If `close_date < open_date`, set `status = "unknown"`, keep
both `*_raw`, and append `{"kind": "conflicting_dates", "excerpt": "<open> / <close>"}`
to `text_mentions`. Never silently pick one.

### 5.3 Document taxonomy (`doc_type` enum)

Canonical types — this is a **vocabulary**, not scheme-specific hardcoding. It
mirrors the existing precedent in `backend/app/document_processing/normalizer.py`
(`GENDER_SPEC`, `IRRIGATION_SPEC`: `Canonical -> {synonyms: [...]}` with the
explicit rule *"Unmatched values are left unchanged. No fuzzy matching or
hallucination."*). Use exactly that structure.

```
AADHAAR                  IDENTITY_PROOF           ADDRESS_PROOF
PAN                      VOTER_ID                 RATION_CARD
INCOME_CERTIFICATE       CASTE_CERTIFICATE        DOMICILE_CERTIFICATE
BIRTH_CERTIFICATE        AGE_PROOF                DISABILITY_CERTIFICATE
BANK_ACCOUNT             LAND_RECORD              EDUCATION_CERTIFICATE
PHOTOGRAPH               MOBILE_NUMBER            EMAIL
INCOME_TAX_RETURN        MEDICAL_CERTIFICATE      REGISTRATION_CERTIFICATE
UNDERTAKING              APPLICATION_FORM         PROJECT_REPORT
SIGNATURE                UNKNOWN
```

Matching is **substring/regex over the lower-cased `raw_text`, longest-alias-wins,
first match only**. No fuzzy matching, no edit distance, no LLM. If nothing matches,
`doc_type = "UNKNOWN"`, `display_name = raw_text`, `match_confidence = "none"`.

`match_confidence`:
* `"high"` — alias matched at a word boundary
* `"low"` — alias matched only as a loose substring
* `"none"` — no match

### 5.4 Conditional-requirement detection (deterministic)

Applied to `raw_text` after HTML-unescape and link extraction:

```
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
```

On match → `requirement = "conditional"` and `condition_text` = **the matched span,
verbatim, with surrounding brackets stripped**. `display_name` = `raw_text` with the
matched span removed and whitespace collapsed. If the resulting `display_name` is
empty, keep `raw_text` unchanged.

Never invent a condition. If no pattern matches, `requirement = "mandatory"` and
`condition_text = null` — matching the source's own framing ("Documents Required").

### 5.5 Free-text deadline mentions — verbatim only

```
DEADLINE_PHRASES = r"(last date|closing date|deadline|apply before|due date|last day)"
```

If `eligibility_raw` or `benefits_raw` matches, append to `text_mentions`:
`{"kind": "deadline_phrase", "excerpt": <±120 chars around the match, verbatim>, "field": "<eligibility_raw|benefits_raw>"}`.

**Absolutely forbidden:** parsing a date out of this text into `open_date`/`close_date`.
The excerpt is shown to the user as-is, next to a link to the official page.

### 5.6 Match signals on the recommendation (Phase 8)

Not persisted — computed per request from `passed_rules`, which the RulesEngine
already produces. Shape:

```json
{
  "signal_type": "income_within_limit",
  "field": "income",
  "operator": "<=",
  "scheme_value": 200000,
  "profile_value": 120000,
  "profile_field": "annual_income",
  "text": "Your annual income (₹1,20,000) is within the scheme's ₹2,00,000 limit.",
  "evidence_source": "scheme_rule",
  "rule_provenance": "heuristic"
}
```

`signal_type` mapping (from `rule.field`):

| `rule.field` | `signal_type` |
|---|---|
| `state` | `state_match` |
| `district` | `district_match` |
| `income` | `income_within_limit` |
| `age` | `age_within_range` |
| `gender` | `gender_match` |
| `category` | `social_category_match` |
| `is_differently_abled` | `disability_match` |
| `land_size` | `land_size_within_limit` |
| `farmer_type` | `farmer_type_match` |
| `crop` | `crop_match` |
| `occupation_type` | `occupation_match` |
| `education_level` | `education_match` |
| `employment_status` | `employment_match` |
| anything else | `other_criterion_match` |

`rule_provenance` is read off the scheme document:
`"manual"` if `manually_verified is True`, else `extraction_method` (`"llm"` /
`"heuristic"` / `"fallback"`), else `"unknown"`.

### 5.7 `reason_summary` and `reason_confidence`

`reason_summary` is assembled deterministically:

1. Order signals by a fixed priority list:
   `state_match, district_match, social_category_match, gender_match,
    disability_match, age_within_range, income_within_limit,
    land_size_within_limit, farmer_type_match, occupation_match,
    education_match, employment_match, crop_match, other_criterion_match`
2. Take the first 3.
3. Join: `"Recommended because " + ", ".join(first_two) + " and " + third`
   (each clause is the signal's `text` with the leading "Your " lower-cased into the
   sentence). If more than 3 signals exist, append `" (+N more matching criteria)"`.
4. If `signals` is empty (possible only if `passed_rules` is empty, which the
   RulesEngine forbids for eligible schemes — but defend anyway), emit exactly:
   `"This scheme is listed because your profile did not fail any of the eligibility
   criteria we could extract from the official scheme page."` and set
   `reason_confidence = "low"`.

`reason_confidence`:

| Condition | Value |
|---|---|
| `scheme.manually_verified is True` | `"verified"` |
| `extraction_method == "llm"` and `len(signals) >= 2` | `"high"` |
| `extraction_confidence == "high"` and `len(signals) >= 3` | `"high"` |
| `len(signals) >= 2` | `"medium"` |
| otherwise | `"low"` |

### 5.8 LLM policy (explicit)

**No LLM is added by this feature.** The recommendation reason is 100 %
deterministic and derived from `passed_rules`, which are themselves auditable rows
in the scheme document.

The one existing LLM (`rule_extractor.py`, Gemini `gemini-2.0-flash`) stays exactly
where it is — at ingestion, producing `rules[]`. It never sees the user's profile and
never writes user-facing prose. Its output is bounded by `_is_constraining_rule()`
and `_parse_llm_response()` validation that already exist.

Deterministic alternative: already the primary path. Fallback: none needed.

---

# PART IV — IMPLEMENTATION

> Phases are dependency-ordered. Do them **in order**. Each phase must leave the app
> in a working state.

## Phase 0 — Test harness bootstrap

**Goal.** Make the rest of the plan testable. There is currently **no test suite and
no pytest installed**.

**Why.** Every subsequent phase specifies tests. Without this they cannot run.

**Files to create**
* `backend/requirements-dev.txt`
  ```
  pytest>=8.0
  pytest-asyncio>=0.24
  respx>=0.21
  ```
* `backend/pytest.ini`
  ```ini
  [pytest]
  testpaths = tests
  asyncio_mode = auto
  pythonpath = .
  ```
* `backend/tests/__init__.py` (empty)
* `backend/tests/conftest.py` — fixtures:
  * `sample_documents_payload` — the verbatim `pm-kisan` `/documents` JSON from §2.2
  * `sample_documents_payload_ast_only` — same but with `documentsRequired_md` removed
  * `sample_documents_payload_empty` — `{"status":"Success","data":null}`
  * `sample_detail_payload` — the verbatim `pm-kisan` detail JSON (5 `en` keys, `data._id`)
  * `sample_search_item` — the verbatim `sui` search item incl. `schemeCloseDate: "2025-03-31"`

**Do NOT** add these to `backend/requirements.txt` — keep runtime deps unchanged.

**Validation.** `cd backend && venv/Scripts/python.exe -m pytest -q` collects 0 tests and exits 0 (or 5).

**Expected outcome.** `pytest` runnable.

---

## Phase 1 — Document taxonomy module

**Goal.** A closed, auditable vocabulary for classifying document requirement strings.

**Why.** `doc_type` is derived data; it must come from one reviewable table, not
scattered `if` statements. Follows the `SemanticNormalizer` precedent.

**File to create:** `backend/app/services/crawler/document_taxonomy.py`

**Contents**

```python
"""
Document Requirement Taxonomy
=============================
Canonical document types + alias vocabulary for classifying the free-text
document requirement lines published by myScheme.gov.in.

Mirrors the design of app/document_processing/normalizer.py:
  Canonical -> {"aliases": [...]}
Unmatched values are left unchanged and typed UNKNOWN.
No fuzzy matching. No LLM. No hallucination.
"""

DOCUMENT_SPEC: dict[str, dict[str, list[str]]] = {
    "AADHAAR": {"aliases": ["aadhaar card", "aadhar card", "aadhaar", "aadhar",
                             "aadhaar number", "aadhaar details", "uid card"]},
    "PAN": {"aliases": ["pan card", "pan number", "permanent account number"]},
    "VOTER_ID": {"aliases": ["voter id", "voter card", "voter identity card",
                              "epic card", "election card"]},
    "IDENTITY_PROOF": {"aliases": ["identity proof", "proof of identity", "id proof",
                                    "photo identification", "government-issued photo"]},
    "ADDRESS_PROOF": {"aliases": ["address proof", "proof of address", "proof of residence",
                                   "residence proof", "residential certificate",
                                   "residence certificate"]},
    "DOMICILE_CERTIFICATE": {"aliases": ["domicile certificate", "permanent resident certificate",
                                          "indigenous inhabitant certificate",
                                          "sikkim subject certificate",
                                          "certificate of identification"]},
    "RATION_CARD": {"aliases": ["ration card", "barcoded ration card"]},
    "INCOME_CERTIFICATE": {"aliases": ["income certificate", "income proof",
                                        "proof of income", "salary certificate"]},
    "INCOME_TAX_RETURN": {"aliases": ["income tax return", "itr", "tax return"]},
    "CASTE_CERTIFICATE": {"aliases": ["caste certificate", "scheduled caste certificate",
                                       "scheduled tribe certificate", "st certificate",
                                       "sc certificate", "obc certificate",
                                       "community certificate"]},
    "BIRTH_CERTIFICATE": {"aliases": ["birth certificate"]},
    "AGE_PROOF": {"aliases": ["age proof", "proof of age", "date of birth certificate"]},
    "DISABILITY_CERTIFICATE": {"aliases": ["disability certificate", "divyang certificate",
                                            "handicap certificate", "udid card"]},
    "BANK_ACCOUNT": {"aliases": ["bank account", "bank passbook", "passbook",
                                  "savings bank account", "cancelled cheque",
                                  "bank account details", "bank statement"]},
    "LAND_RECORD": {"aliases": ["landholding paper", "land ownership document",
                                 "7/12", "satbara", "8-a record", "khasra",
                                 "proof of agricultural land", "land record",
                                 "proof of land", "lease agreement"]},
    "EDUCATION_CERTIFICATE": {"aliases": ["mark sheet", "marksheet", "matriculation certificate",
                                           "school leaving certificate", "passing certificate",
                                           "degree certificate", "educational certificate",
                                           "proof of admission", "course structure"]},
    "PHOTOGRAPH": {"aliases": ["passport size photo", "passport-size photograph",
                                "photograph", "photo"]},
    "SIGNATURE": {"aliases": ["signature"]},
    "MOBILE_NUMBER": {"aliases": ["mobile number", "mobile no"]},
    "EMAIL": {"aliases": ["email id", "e-mail id", "email address"]},
    "MEDICAL_CERTIFICATE": {"aliases": ["medical certificate", "doctor's certificate",
                                         "doctors certificate", "health certificate"]},
    "REGISTRATION_CERTIFICATE": {"aliases": ["registration certificate", "registration card",
                                              "worker registration card", "registration proof",
                                              "kisan credit card", "kcc"]},
    "UNDERTAKING": {"aliases": ["undertaking", "affidavit", "self-declaration",
                                 "self declaration", "self-certificate"]},
    "APPLICATION_FORM": {"aliases": ["application form", "common application form",
                                      "filled application"]},
    "PROJECT_REPORT": {"aliases": ["project report", "detailed project report", "dpr"]},
}

UNKNOWN_DOC_TYPE = "UNKNOWN"
TAXONOMY_VERSION = 1
```

Plus one public function:

```python
def classify_document(text: str) -> tuple[str, str]:
    """
    Return (doc_type, match_confidence).
    Longest alias wins. Word-boundary match -> "high", loose substring -> "low",
    no match -> (UNKNOWN_DOC_TYPE, "none").
    """
```

**Implementation logic.** Build a module-level list of `(alias, doc_type)` sorted by
`len(alias)` descending, once at import. For each alias, first try
`re.search(rf"\b{re.escape(alias)}\b", lowered)` → `"high"`; collect loose
`alias in lowered` matches as a fallback → `"low"`. Return the first high match,
else the first low match, else `(UNKNOWN, "none")`.

**Dependencies.** None.

**Tests** — `backend/tests/test_document_taxonomy.py`:
* `"Aadhaar Card."` → `("AADHAAR", "high")`
* `"Landholding papers."` → `("LAND_RECORD", "high")`
* `"Savings Bank Account."` → `("BANK_ACCOUNT", "high")`
* `"Scheduled Tribe Certificate for APST patients"` → `("CASTE_CERTIFICATE", "high")`
* `"Some entirely novel state-specific form XYZ-9"` → `("UNKNOWN", "none")`
* longest-alias-wins: `"Income Tax Return"` → `INCOME_TAX_RETURN`, not `INCOME_CERTIFICATE`

**Expected outcome.** Pure module, importable, fully unit-tested, no I/O.

---

## Phase 2 — Document requirement extractor

**Goal.** Turn a `/documents` API payload into the `required_documents` sub-document
from §5.1.

**File to create:** `backend/app/services/crawler/document_extractor.py`

**Public API**

```python
EXTRACTOR_VERSION = 1

def flatten_documents_ast(nodes: list) -> list[str]:
    """Walk the Slate-style AST, returning one string per `type == "list_item"`."""

def parse_documents_markdown(md: str) -> list[str]:
    """Parse an ordered/unordered markdown list into one string per item.
    Handles myScheme's malformed '1. A1. B' run-on lists (see §2.2)."""

def normalize_document_line(raw: str) -> dict | None:
    """raw -> one items[] entry (§5.1). Returns None for empty/whitespace lines."""

def build_required_documents(
    documents_payload: dict | None,
    *,
    source_url: str | None,
    fetched_at: datetime,
    fetch_failed: bool = False,
) -> dict:
    """Full required_documents sub-document. Never raises."""
```

**Implementation logic (exact order — do not reorder)**

`normalize_document_line(raw)`:
1. `html.unescape(raw)` **twice** — the DB shows double-escaped entities
   (`&amp;amp;#39;`), so one pass is not enough. Guard: stop if a pass is a no-op.
2. Extract markdown links with `re.findall(r"\[([^\]]*)\]\(([^)]+)\)", text)`.
   Push each URL into `links[]`; replace `[label](url)` with `label`.
3. Strip a leading list marker: `re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", text)`.
4. Collapse whitespace: `re.sub(r"\s+", " ", text).strip()`.
5. Strip a single trailing `.` **only** if the remaining text has no other `.`
   (so `"Aadhaar Card."` → `"Aadhaar Card"` but `"Rs. 5 lakh proof."` keeps its dots).
   Keep the pre-strip value as `raw_text`.
6. If the result is empty or shorter than 3 characters → return `None`.
7. Apply §5.4 conditional detection → `requirement`, `condition_text`, `display_name`.
8. `doc_type, match_confidence = classify_document(display_name or raw_text)`.
9. If `doc_type == "UNKNOWN"`, set `display_name = raw_text`.

`build_required_documents(...)`:
* `fetch_failed=True` → `{"status": "fetch_failed", "items": [], "item_count": 0, …}`
  and **do not** touch any previously stored value (the caller enforces this — see Phase 5).
* `documents_payload is None` or `payload["data"] is None` or `data` is not a dict
  → `status = "unavailable"`, `items = []`.
* Otherwise read `data["en"]["documentsRequired_md"]` and
  `data["en"]["documents_required"]`.
  * Prefer AST → `flatten_documents_ast`. If it yields ≥ 1 item, use it.
  * Else use markdown → `parse_documents_markdown`.
  * If both yield 0 items → `status = "unavailable"`, but **still store
    `raw_markdown`** if present (provenance).
* De-duplicate items by case-folded `raw_text`, preserving first-seen order.
* Cap `items` at **40**; if the source had more, keep the first 40 and record the
  true count in `item_count`. (Largest observed: 13. The cap is a defence against a
  source-format change producing thousands of fragments.)

`parse_documents_markdown` must handle the observed malformed run-on
`1. [Undertaking](url)1. [Work Slip](url)` — split on `(?=(?:^|\s)\d+[.)]\s)` in
addition to newlines.

**Dependencies.** Phase 1.

**Tests** — `backend/tests/test_document_extractor.py`:
* pm-kisan payload → 3 items, all `mandatory`, types `AADHAAR`/`LAND_RECORD`/`BANK_ACCOUNT`
* AST-only payload (no `_md`) → same item count
* markdown-only payload (empty AST) → items parsed from markdown
* `{"data": null}` → `status == "unavailable"`, `items == []`
* `fetch_failed=True` → `status == "fetch_failed"`
* `"Caste Certificate (If applicable)"` → `requirement == "conditional"`,
  `condition_text == "If applicable"`, `display_name == "Caste Certificate"`
* `"[Undertaking](https://x/y.pdf)"` → `raw_text == "Undertaking"`,
  `links == ["https://x/y.pdf"]`
* double-escaped `"Applicant&amp;amp;#39;s photo"` → `"Applicant's photo"`
* run-on `"1. [A](u1)1. [B](u2)"` → 2 items
* duplicate lines → deduplicated
* **idempotency:** `build_required_documents(p) == build_required_documents(p)`

**Expected outcome.** Pure, deterministic, never raises.

---

## Phase 3 — Application timeline extractor

**Goal.** Produce the `application_timeline` sub-document from §5.2.

**File to create:** `backend/app/services/crawler/timeline_extractor.py`

**Public API**

```python
EXTRACTOR_VERSION = 1
IST = ZoneInfo("Asia/Kolkata")   # with a fixed timezone(timedelta(hours=5, minutes=30)) fallback

def parse_source_date(raw: str | None) -> datetime | None:
    """Strict YYYY-MM-DD -> UTC-midnight datetime. Anything else -> None."""

def find_deadline_mentions(eligibility_raw: str, benefits_raw: str) -> list[dict]:
    """Verbatim ±120-char excerpts around DEADLINE_PHRASES. Never parses a date."""

def build_application_timeline(
    *,
    open_date_raw: str | None,
    close_date_raw: str | None,
    application_process: list | None,
    eligibility_raw: str | None,
    benefits_raw: str | None,
    fetched_at: datetime,
) -> dict:
    """Full application_timeline sub-document. Never raises."""

def evaluate_timeline_state(timeline: dict | None, today_ist: date | None = None) -> dict:
    """READ-TIME derivation — never persisted.
    Returns {"state", "days_remaining", "label"}."""
```

`evaluate_timeline_state` output contract:

| Condition | `state` | `days_remaining` | `label` |
|---|---|---|---|
| `timeline is None` or `status == "unknown"` and no mentions | `"unknown"` | `null` | `"Application deadline not published"` |
| `status == "window"` and `close_date.date() >= today_ist` | `"open"` | `(close - today).days` | `"Apply by 31 Mar 2025"` |
| `status == "window"` and `close_date.date() < today_ist` | `"expired"` | negative int | `"Closed on 31 Mar 2025"` |
| `status == "window"` and `0 <= days_remaining <= 30` | `"closing_soon"` | int | `"Closes in 12 days"` |
| `status == "open_ended"` | `"open_ended"` | `null` | `"Open — no closing date published"` |
| `status == "unknown"` but `text_mentions` non-empty | `"unknown_with_mention"` | `null` | `"See official page for dates"` |

`"closing_soon"` is checked before `"open"`.

Date formatting is `"%d %b %Y"` (e.g. `31 Mar 2025`) — a fixed, unambiguous format,
not locale-dependent.

**Dependencies.** None.

**Tests** — `backend/tests/test_timeline_extractor.py`:
* `parse_source_date("2019-02-24")` → UTC midnight 2019-02-24
* `parse_source_date("24/02/2019")` → `None`
* `parse_source_date("")` / `None` → `None`
* open only → `status == "open_ended"`
* open + close → `status == "window"`
* neither → `status == "unknown"`
* `close_date < open_date` → `status == "unknown"` and a `conflicting_dates` mention,
  **both** `*_raw` preserved
* unparseable close date → `close_date is None`, `close_date_raw` preserved,
  `unparseable_date` mention present
* `evaluate_timeline_state` with `today_ist=date(2026,9,8)` and
  `close_date=2026-09-08` → `"closing_soon"`, `days_remaining == 0` (**boundary: still open**)
* same with `close_date=2026-09-07` → `"expired"`
* same with `close_date=2026-12-31` → `"open"`
* `find_deadline_mentions` returns a verbatim excerpt and **never** a date field

**Expected outcome.** Pure, deterministic, timezone-correct.

---

## Phase 4 — Fetcher & parser: reach the new endpoint

**Goal.** Fetch `/documents` and surface the Mongo ObjectId and the raw dates.

### 4a. `backend/app/services/crawler/fetcher.py`

Add **one** method to `MySchemeApiFetcher` (do not change existing methods):

```python
async def fetch_scheme_documents(self, client: httpx.AsyncClient,
                                 scheme_object_id: str) -> Optional[Dict]:
    """
    Fetch the 'Documents Required' sub-resource for one scheme.

    Endpoint (reverse-engineered from myscheme.gov.in DevTools, 2026-09-08):
        GET /schemes/v6/public/schemes/{scheme_object_id}/documents?lang=en

    scheme_object_id is the Mongo ObjectId from the detail response
    (detail["data"]["_id"]) — NOT the Elasticsearch id from the search endpoint.

    Returns the parsed JSON body, or None on transport failure.
    A body of {"status": "Success", "data": null} means the scheme has no
    documents section and IS returned as-is (it is a valid 'unavailable' answer).
    """
    if not scheme_object_id:
        return None
    url = f"{self.base_url}/schemes/v6/public/schemes/{scheme_object_id}/documents"
    resp = await self._request_with_retry(client, url, {"lang": "en"})
    if resp is None or resp.status_code != 200:
        logger.warning(...)
        return None
    try:
        return resp.json()
    except Exception as exc:
        logger.warning(...)
        return None
```

Reuse `_request_with_retry` and `_build_headers` unchanged — they already implement
the retry/backoff and browser-like headers that this API requires.

Also add, mirroring `fetch_details_batch`:

```python
async def fetch_documents_batch(self, object_ids: Dict[str, str],
                                max_concurrency: int = 2) -> Dict[str, Optional[Dict]]:
    """slug -> object_id  ==>  slug -> documents payload (or None)."""
```

Use the **same** `asyncio.Semaphore(max_concurrency)` + `await asyncio.sleep(0.5)`
politeness pattern as `fetch_details_batch`. Do not raise the concurrency.

### 4b. `backend/app/services/crawler/parser.py`

In `MySchemeParser.parse_detail()`, add to the returned dict — **do not remove or
rename any existing key**:

```python
"myscheme_object_id": detail_payload.get("data", {}).get("_id"),
"application_modes": [
    {"mode": ap.get("mode"), "url": ap.get("url")}
    for ap in (en.get("applicationProcess") or [])
    if isinstance(ap, dict) and ap.get("mode")
],
```

`scheme_open_date` is already returned — leave it.
`close_date` is already returned by `parse_summary()` — leave it.

Add a new static method:

```python
@staticmethod
def parse_documents(documents_payload: Optional[Dict]) -> Optional[Dict]:
    """
    Narrow the /documents response to {'documentsRequired_md', 'documents_required'}
    or None when the scheme has no documents section.
    """
```

**Dependencies.** None (Phases 1–3 are independent).

**Tests** — `backend/tests/test_crawler_parser.py`:
* `parse_detail(sample_detail_payload)["myscheme_object_id"] == "62a70e86f038bd8499a6aa53"`
* `parse_detail(...)["application_modes"]` has 2 entries with the right modes/urls
* `parse_detail({})` returns all keys with safe defaults (no `KeyError`)
* `parse_summary(sample_search_item["fields"])["close_date"] == "2025-03-31"`
* `parse_documents({"data": None})` → `None`

Use `respx` to assert `fetch_scheme_documents` hits exactly
`/schemes/v6/public/schemes/<id>/documents` with `lang=en`, and returns `None` on 500.

**Expected outcome.** The crawler can reach the documents endpoint. Nothing is
persisted yet — the app behaves exactly as before.

---

## Phase 5 — Normalizer & scheduler: persist the enrichment

**Goal.** Write `required_documents` and `application_timeline` into the `schemes`
collection on every ingestion cycle, idempotently, without breaking the existing
`manually_verified` protection.

### 5a. `backend/app/services/crawler/normalizer.py`

In `MySchemeNormalizer.normalize()`, **after** the existing `normalized = {...}`
dict literal and **before** `normalized["content_hash"] = ...`, add:

```python
        # --- New: enrichment inputs carried through from parser (previously dropped) ---
        normalized["myscheme_object_id"] = parsed_record.get("myscheme_object_id")
        normalized["scheme_open_date_raw"] = parsed_record.get("scheme_open_date")
        normalized["scheme_close_date_raw"] = parsed_record.get("close_date")

        normalized["application_timeline"] = build_application_timeline(
            open_date_raw=parsed_record.get("scheme_open_date"),
            close_date_raw=parsed_record.get("close_date"),
            application_process=parsed_record.get("application_modes"),
            eligibility_raw=normalized["eligibility_raw"],
            benefits_raw=normalized["benefits_raw"],
            fetched_at=now,
        )
```

`required_documents` is **not** built here — the normalizer has no HTTP client. The
scheduler attaches it (5b).

**Do NOT change `compute_content_hash`.** It currently hashes
`name + description + eligibility_raw`. Adding enrichment to the hash would mark all
4,788 schemes as changed on the first run and fire 4,788 `scheme_change_events`.

### 5b. `backend/app/services/crawler/scheduler.py`

Inside `run_ingestion_cycle`, **Step 3**, after `details = await self.fetcher.fetch_details_batch(slugs_to_fetch)`:

```python
        # Step 3b — Fetch the Documents Required sub-resource for each fetched scheme.
        # Keyed by the Mongo ObjectId in the detail payload, not the search id.
        object_ids: Dict[str, str] = {}
        for slug, payload in details.items():
            oid = ((payload or {}).get("data") or {}).get("_id")
            if oid:
                object_ids[slug] = oid
        documents_payloads = await self.fetcher.fetch_documents_batch(object_ids) \
            if object_ids else {}
```

Add `"documents_fetched": 0`, `"documents_missing": 0`, `"documents_failed": 0` to
the `stats` dict initialiser.

Inside `process_one_scheme(slug)`, immediately after
`normalized = self.normalizer.normalize(merged)`:

```python
                    # --- Required documents enrichment -------------------------------
                    doc_payload = documents_payloads.get(slug, "__not_fetched__")
                    fetch_failed = (slug in object_ids and doc_payload is None)
                    normalized["required_documents"] = build_required_documents(
                        None if doc_payload == "__not_fetched__" else doc_payload,
                        source_url=normalized.get("source_url"),
                        fetched_at=normalized["last_fetched"],
                        fetch_failed=fetch_failed,
                    )
                    _st = normalized["required_documents"]["status"]
                    if _st == "available":
                        stats["documents_fetched"] += 1
                    elif _st == "fetch_failed":
                        stats["documents_failed"] += 1
                    else:
                        stats["documents_missing"] += 1
```

**Never destroy good data on a failed fetch.** In the `if existing:` branch, before
building `update_fields`:

```python
                        # Enrichment write policy:
                        #  - manually_verified  -> never overwrite enrichment at all
                        #  - fetch_failed       -> keep whatever we already had
                        #  - otherwise          -> replace wholesale (idempotent)
                        if existing.get("manually_verified") is True:
                            if existing.get("required_documents"):
                                normalized["required_documents"] = existing["required_documents"]
                            if existing.get("application_timeline"):
                                normalized["application_timeline"] = existing["application_timeline"]
                        elif normalized["required_documents"]["status"] == "fetch_failed" \
                                and existing.get("required_documents", {}).get("status") == "available":
                            normalized["required_documents"] = existing["required_documents"]
```

Then add to `update_fields`:

```python
                            "myscheme_object_id": normalized.get("myscheme_object_id"),
                            "scheme_open_date_raw": normalized.get("scheme_open_date_raw"),
                            "scheme_close_date_raw": normalized.get("scheme_close_date_raw"),
                            "required_documents": normalized["required_documents"],
                            "application_timeline": normalized["application_timeline"],
```

Extend the `changed_fields` diff with:

```python
                        if (existing.get("required_documents") or {}).get("items") != \
                           (normalized.get("required_documents") or {}).get("items"):
                            changed_fields.append("documents")
                        _et = (existing.get("application_timeline") or {})
                        _nt = (normalized.get("application_timeline") or {})
                        if (_et.get("open_date_raw"), _et.get("close_date_raw")) != \
                           (_nt.get("open_date_raw"), _nt.get("close_date_raw")):
                            changed_fields.append("timeline")
```

Finally, add `documents_fetched` / `documents_missing` / `documents_failed` to the
`_log_run` `log_entry`.

**Dependencies.** Phases 1–4.

**Validation.**
```
cd backend
venv/Scripts/python.exe -c "import asyncio; from app.services.crawler.scheduler import MySchemeIngestionScheduler as S; print(asyncio.run(S().run_ingestion_cycle(limit=5)))"
```
Expect `documents_fetched + documents_missing == 5` and 0 errors. Then inspect one
document in Mongo and confirm `required_documents.items` and
`application_timeline.status` are populated.

**Tests** — `backend/tests/test_ingestion_enrichment.py`: with `respx` mocking all
three endpoints and a fake in-memory db double, assert
(a) a fresh scheme is inserted with both sub-documents;
(b) running twice produces an identical document (idempotency);
(c) a `manually_verified: True` existing doc keeps its enrichment untouched;
(d) a documents fetch failure preserves previously-stored `available` documents.

**Expected outcome.** New ingestion cycles persist enrichment. Existing schemes are
untouched until Phase 6.

---

## Phase 6 — Backfill script + indexes

**Goal.** Enrich the 4,788 already-stored schemes without a 35-minute full
re-ingest, and add the indexes the recommendation query needs.

**File to create:** `backend/scripts/backfill_scheme_enrichment.py`

Model it on `backend/scripts/seed_schemes.py` (same `sys.path` bootstrap, same
`AsyncIOMotorClient` construction from `settings`).

**CLI**

```
--limit N            process at most N schemes (default: all)
--slug SLUG          process exactly one scheme (repeatable)
--dry-run            compute and report, write nothing
--force              re-enrich even when required_documents.status == "available"
                     and extractor_version matches
--concurrency N      default 2 (matches the polite ingestion default)
--offline            derive application_timeline from already-stored fields only;
                     make no HTTP calls
```

**Selection query** (resumable — a re-run picks up where it stopped):

```python
{"$or": [
    {"required_documents": {"$exists": False}},
    {"required_documents.status": {"$in": ["fetch_failed", "not_fetched"]}},
    {"required_documents.extractor_version": {"$ne": DOC_EXTRACTOR_VERSION}},
]}
```
`--force` drops the filter entirely.

**Per scheme**
1. `slug = doc["myscheme_slug"]`. If falsy (9 YAML-seeded docs), write
   `required_documents = {status: "unavailable", source: "not_from_myscheme", …}`
   and `application_timeline = {status: "unknown", …}`, then continue — no HTTP.
2. `object_id = doc.get("myscheme_object_id")`. If absent, call
   `fetch_scheme_detail(client, slug)` to obtain `data._id` and persist it.
3. `fetch_scheme_documents(client, object_id)` → `build_required_documents(...)`.
4. `build_application_timeline(...)` from `doc["scheme_open_date_raw"]`,
   `doc["scheme_close_date_raw"]`, `doc.get("application_modes")`,
   `doc["eligibility_raw"]`, `doc["benefits_raw"]`. (For rows backfilled before a
   re-ingest, the `*_raw` dates will be absent → `status = "unknown"`. That is
   correct and honest; the next daily ingestion fills them in.)
5. Update **by `_id`**, never by `scheme_id` (8 duplicate groups) and never by
   `myscheme_slug` alone (9 duplicate groups):
   ```python
   await db["schemes"].update_one({"_id": doc["_id"]}, {"$set": {...}})
   ```
6. Respect `manually_verified` exactly as Phase 5b does.
7. `await asyncio.sleep(0.5)` between HTTP calls; `asyncio.Semaphore(concurrency)`.
8. Log progress every 100; write one summary row into `scheme_ingestion_log` with
   `{"type": "enrichment_backfill", …}`.

**Indexes** — add an idempotent block at the end of the script (and only there; do
not add index creation to `main.py` startup, which would slow every boot):

```python
await db["schemes"].create_index(
    [("status", 1), ("myscheme_slug", 1)], name="ix_status_slug")
await db["schemes"].create_index("myscheme_slug", name="ix_slug")
await db["schemes"].create_index("myscheme_object_id", name="ix_object_id", sparse=True)
await db["schemes"].create_index("scheme_id", name="ix_scheme_id")
```

**Do NOT create a unique index** on `scheme_id` or `myscheme_slug` — 8 and 9
duplicate groups exist and index creation would fail. De-duplication is a separate
piece of work, out of scope.

**Estimated runtime.** 4,788 schemes ÷ concurrency 2 × ~0.9 s ≈ **36 minutes**.
Run it once, off-peak. It is fully resumable.

**Dependencies.** Phases 1–5.

**Validation.**
```
venv/Scripts/python.exe scripts/backfill_scheme_enrichment.py --limit 20 --dry-run
venv/Scripts/python.exe scripts/backfill_scheme_enrichment.py --limit 20
venv/Scripts/python.exe scripts/backfill_scheme_enrichment.py --limit 20   # must report 0 processed
```
The third run proving 0 work remains is the idempotency check.

**Expected outcome.** Existing schemes enriched; indexes present; recommendation
behaviour still unchanged (nothing reads the new fields yet).

---

## Phase 7 — Evidence & explanation in the recommendation engine

**Goal.** Emit structured `match_signals` + `reason_summary` + `reason_confidence`,
and attach the persisted enrichment to each eligible scheme.

### 7a. `backend/app/ml/explainability/scheme_explainer.py`

**Add** to `SchemeExplainer` — do **not** modify or remove `explain_eligible`,
`explain_ineligible`, or `_translate_rule`. The Dashboard renders
`scheme.explanation` today and must keep working.

```python
    SIGNAL_TYPE_BY_FIELD = { ... }          # §5.6 table
    SIGNAL_PRIORITY = [ ... ]               # §5.7 ordering
    PROFILE_FIELD_BY_RULE_FIELD = {
        "income": "annual_income",
        "land_size": "land_size_hectares",
        "crop": "primary_crops",
        "occupation_type": "occupation",
        "is_differently_abled": "is_differently_abled",
    }

    @staticmethod
    def build_match_signals(passed_rules: list, rule_provenance: str) -> list[dict]:
        """One MatchSignal (§5.6) per passed rule. Deterministic. Never invents."""

    @staticmethod
    def build_reason_summary(signals: list[dict]) -> str:
        """§5.7. Deterministic assembly. No LLM."""

    @staticmethod
    def compute_reason_confidence(signals: list[dict], scheme: dict) -> str:
        """§5.7 confidence table."""
```

`build_match_signals` sentence templates (exhaustive — `{v}` is `scheme_value`,
`{f}` is `profile_value`):

| operator | text |
|---|---|
| `==` (`state`) | `Your state ({f}) matches the scheme's state ({v}).` |
| `==` (`gender`) | `The scheme is for {v} applicants, matching your profile.` |
| `==` (`category`) | `The scheme targets the {v} category, matching your profile.` |
| `==` (`is_differently_abled`) | `The scheme is for applicants with a disability, matching your profile.` |
| `==` (other) | `Your {label} ({f}) matches the required value ({v}).` |
| `in` | `Your {label} ({f}) is one of the eligible values ({v_joined}).` |
| `<=` / `<` (`income`) | `Your annual income (₹{f:,}) is within the scheme's ₹{v:,} limit.` |
| `<=` / `<` (`land_size`) | `Your land holding ({f} ha) is within the scheme's {v} ha limit.` |
| `<=` / `<` (`age`) | `Your age ({f}) is within the scheme's maximum of {v}.` |
| `<=` / `<` (other) | `Your {label} ({f}) is within the scheme's limit of {v}.` |
| `>=` / `>` (`age`) | `Your age ({f}) meets the scheme's minimum of {v}.` |
| `>=` / `>` (other) | `Your {label} ({f}) meets the scheme's minimum of {v}.` |
| `!=` / `not_in` | `Your {label} ({f}) is not in the excluded set.` |

`{label}` comes from a `FIELD_LABELS` dict; unknown fields fall back to
`field.replace("_", " ").title()`.

**Formatting guard:** `profile_value` may be a list (`primary_crops`) or a bool.
Render lists as `", ".join(...)` and bools as `Yes`/`No`. Never `str(dict)`.

### 7b. `backend/app/ml/inference/ranking_engine.py`

In `rank_schemes`, inside the **eligible** loop (`for scheme_idx, scheme in enumerate(eligible_schemes)`),
after `explanation = SchemeExplainer.explain_eligible(...)`:

```python
            rule_provenance = (
                "manual" if scheme.get("manually_verified") is True
                else (scheme.get("extraction_method") or "unknown")
            )
            match_signals = SchemeExplainer.build_match_signals(
                scheme.get("passed_rules", []), rule_provenance
            )
            reason_summary = SchemeExplainer.build_reason_summary(match_signals)
            reason_confidence = SchemeExplainer.compute_reason_confidence(match_signals, scheme)
```

Add to the `ranked_results.append({...})` literal — **append only, change nothing existing**:

```python
                "match_signals": match_signals[:6],
                "reason_summary": reason_summary,
                "reason_confidence": reason_confidence,
                "required_documents": _public_documents(scheme.get("required_documents")),
                "application_timeline": scheme.get("application_timeline"),
                "timeline_state": evaluate_timeline_state(scheme.get("application_timeline")),
```

Add a module-level helper in `ranking_engine.py`:

```python
def _public_documents(rd: dict | None) -> dict | None:
    """Strip raw_markdown from the API-facing copy — it is provenance, not payload.
    Keeps the /farmers/me response ~30% smaller. The full record with raw_markdown
    stays in Mongo and is served by GET /api/schemes/{id}/requirements."""
    if not rd:
        return None
    return {k: v for k, v in rd.items() if k != "raw_markdown"}
```

**Do NOT touch the ineligible loop.** It already returns 4,652 entries / 1.43 MB;
attaching ~1.8 KB each would add ~8 MB to every `GET /api/farmers/me`.

**Measured payload impact of the eligible-only change** (114 eligible for the test
farmer, duplicated once into `recommended_bundles`):
`recommended_schemes` 97 KB → ~190 KB; `recommended_bundles` 97 KB → ~190 KB.
Total response grows ~190 KB against a 1.6 MB baseline. Acceptable.
The `match_signals[:6]` cap and the `raw_markdown` strip are what keep it there —
**do not remove either.**

**Dependencies.** Phases 1–3, 6.

**Tests** — `backend/tests/test_scheme_explainer.py`:
* `build_match_signals` on a real `passed_rules` list produces one signal per rule,
  every signal has all 9 keys, and `signal_type` maps correctly
* `income` rule with `value=200000, farmer_value=120000` →
  text contains `₹1,20,000` and `₹2,00,000`
* empty `passed_rules` → `[]`, and `build_reason_summary([])` returns the
  documented no-signal sentence
* 5 signals → summary contains exactly 3 clauses + `"(+2 more matching criteria)"`
* signal ordering follows `SIGNAL_PRIORITY` regardless of input order
* `compute_reason_confidence` returns `"verified"` for `manually_verified: True`
* `primary_crops` list-valued `profile_value` renders as a comma string, not `['a']`
* **no fabrication:** every number appearing in every `text` also appears in the
  input rule dict (assert this programmatically)

`backend/tests/test_ranking_enrichment.py`: run `rank_schemes` against 3 synthetic
scheme dicts and assert the 6 new keys are present on eligible results and
**absent** on ineligible results.

**Expected outcome.** The engine emits evidence. The API still strips it (Phase 8).

---

## Phase 8 — API contract

**Goal.** Let the new fields reach the client, and add a detail endpoint.

### 8a. `backend/app/models/farmer.py` — REQUIRED, or everything is silently dropped

Add these models above `SchemeRecommendation`:

```python
class MatchSignal(BaseModel):
    signal_type: str
    field: str
    operator: str
    scheme_value: Any = None
    profile_value: Any = None
    profile_field: Optional[str] = None
    text: str
    evidence_source: str = "scheme_rule"
    rule_provenance: str = "unknown"


class RequiredDocumentItem(BaseModel):
    raw_text: str
    display_name: str
    doc_type: str = "UNKNOWN"
    requirement: str = "mandatory"
    condition_text: Optional[str] = None
    match_confidence: str = "none"
    links: List[str] = []


class RequiredDocuments(BaseModel):
    status: str = "not_fetched"
    source: Optional[str] = None
    source_url: Optional[str] = None
    fetched_at: Optional[datetime] = None
    items: List[RequiredDocumentItem] = []
    item_count: int = 0
    unmatched_count: int = 0
    extractor_version: int = 1


class ApplicationMode(BaseModel):
    mode: str
    url: Optional[str] = None


class TimelineMention(BaseModel):
    kind: str
    excerpt: str
    field: Optional[str] = None


class ApplicationTimeline(BaseModel):
    status: str = "unknown"
    open_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    open_date_raw: Optional[str] = None
    close_date_raw: Optional[str] = None
    open_date_source: Optional[str] = None
    close_date_source: Optional[str] = None
    application_modes: List[ApplicationMode] = []
    text_mentions: List[TimelineMention] = []
    fetched_at: Optional[datetime] = None
    extractor_version: int = 1


class TimelineState(BaseModel):
    state: str = "unknown"
    days_remaining: Optional[int] = None
    label: str = ""
```

Requires `from typing import Any` and `from datetime import datetime` at the top of
`farmer.py` (currently absent — add them).

Then extend `SchemeRecommendation` — **append fields, never reorder or remove**:

```python
class SchemeRecommendation(BaseModel):
    scheme_id: str
    scheme_name: str
    success_probability: float
    explanation: List[str] = []
    predicted_financial_value: int = 0
    benefit_type: str = ""
    prediction_explanation: str = ""
    # --- new: evidence-based reasoning + requirements ---
    source_url: Optional[str] = None            # was produced but silently dropped (PRE-5)
    match_signals: List[MatchSignal] = []
    reason_summary: str = ""
    reason_confidence: str = "low"
    required_documents: Optional[RequiredDocuments] = None
    application_timeline: Optional[ApplicationTimeline] = None
    timeline_state: Optional[TimelineState] = None
```

Adding `source_url` also fixes PRE-5 and lets the Dashboard stop guessing the URL.

**Do not touch `IneligibleScheme`** (payload — see Phase 7b).

`SchemeBundle.schemes` is already `List[SchemeRecommendation]`, so bundles inherit
the new fields automatically. Verify this rather than assuming.

### 8b. `backend/app/api/farmers.py`

1. **Fix PRE-1:** add `from datetime import datetime` to the imports.
2. Change `get_published_schemes` to use a projection. This is a **performance
   improvement**, not a regression — `eligibility_raw` / `benefits_raw` are verified
   unused by the entire ranking path (`grep -rn "eligibility_raw\|benefits_raw"
   backend/app` returns hits only in `models/scheme.py` and the crawler):

```python
SCHEME_PROJECTION = {
    "_id": 1, "scheme_id": 1, "name": 1, "department": 1, "description": 1,
    "category": 1, "level": 1, "state": 1, "benefit_type": 1,
    "benefit_calculation": 1, "conflicts_with": 1, "rules": 1, "status": 1,
    "source_url": 1, "myscheme_slug": 1, "financial_benefit": 1,
    "manually_verified": 1, "extraction_method": 1, "extraction_confidence": 1,
    "required_documents": 1, "application_timeline": 1,
}

async def get_published_schemes(db) -> list | None:
    try:
        cursor = db["schemes"].find(
            {"status": "published", "rules": {"$exists": True, "$ne": []}},
            SCHEME_PROJECTION,
        )
        schemes = await cursor.to_list(length=None)
        return schemes if schemes else None
    except Exception as e:
        logger.warning(f"Could not fetch schemes from MongoDB: {e}")
        return None
```

No other change to `farmers.py`. `GET /api/farmers/me` and `PUT /api/farmers/me`
keep their shapes; the recommendation objects simply carry more fields.

**Backward compatibility:** every new field is additive with a default, so an old
client ignores them. No breaking change.

### 8c. `backend/app/api/schemes.py` — new endpoint

```python
@router.get("/{scheme_id}/requirements")
async def get_scheme_requirements(scheme_id: str):
    """
    Full requirements record for one scheme, including the verbatim source markdown.
    Used by the Dashboard detail dialog and for auditing what we display.
    """
```

* **Method / route:** `GET /api/schemes/{scheme_id}/requirements`
* **Auth:** none — matches the rest of `schemes.py`, which is unauthenticated. The
  data is public government information.
* **Lookup:** identical to the existing `get_scheme_by_id` — `$or` on `scheme_id`
  and, when `ObjectId.is_valid(scheme_id)`, `_id`. Register this route **before**
  `@router.get("/{scheme_id}")` is irrelevant (different suffix), but keep it above
  `/monitoring/logs` ordering conventions.
* **404:** `{"detail": "Scheme '<id>' not found"}` — same as `get_scheme_by_id`.
* **200 response:**

```json
{
  "status": "success",
  "scheme_id": "PM_KISAN",
  "scheme_name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
  "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
  "last_fetched": "2026-09-08T09:14:22.101Z",
  "required_documents": {
    "status": "available",
    "source": "myscheme_documents_api",
    "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
    "fetched_at": "2026-09-08T09:14:22.101Z",
    "raw_markdown": "\n1. Aadhaar Card.\n1. Landholding papers.\n1. Savings Bank Account.\n\n<br>\n\n",
    "items": [
      {"raw_text": "Aadhaar Card", "display_name": "Aadhaar Card", "doc_type": "AADHAAR",
       "requirement": "mandatory", "condition_text": null, "match_confidence": "high", "links": []},
      {"raw_text": "Landholding papers", "display_name": "Landholding papers", "doc_type": "LAND_RECORD",
       "requirement": "mandatory", "condition_text": null, "match_confidence": "high", "links": []},
      {"raw_text": "Savings Bank Account", "display_name": "Savings Bank Account", "doc_type": "BANK_ACCOUNT",
       "requirement": "mandatory", "condition_text": null, "match_confidence": "high", "links": []}
    ],
    "item_count": 3, "unmatched_count": 0, "extractor_version": 1
  },
  "application_timeline": {
    "status": "open_ended",
    "open_date": "2019-02-24T00:00:00Z", "close_date": null,
    "open_date_raw": "2019-02-24", "close_date_raw": null,
    "open_date_source": "myscheme_basic_details.schemeOpenDate",
    "close_date_source": null,
    "application_modes": [
      {"mode": "Online", "url": "https://pmkisan.gov.in/RegistrationFormnew.aspx"},
      {"mode": "Online - via CSC", "url": null}
    ],
    "text_mentions": [], "fetched_at": "2026-09-08T09:14:22.101Z", "extractor_version": 1
  },
  "timeline_state": {"state": "open_ended", "days_remaining": null,
                     "label": "Open — no closing date published"}
}
```

* **Scheme exists but was never enriched:** `required_documents` is
  `{"status": "not_fetched", "items": [], …}` and `application_timeline` is
  `{"status": "unknown", …}`. **200, not 404** — "we don't know" is a real answer.
* **Validation:** none beyond the path param; no query params.
* **Errors:** `500` `{"detail": "Database connection uninitialized"}` when `get_db()`
  returns `None`, matching the rest of the file.

**Dependencies.** Phase 7.

**Tests** — `backend/tests/test_api_contract.py`:
* `SchemeRecommendation.model_validate({...with all new fields...}).model_dump()`
  **retains** `source_url`, `match_signals`, `reason_summary`, `required_documents`,
  `application_timeline`, `timeline_state` (this is the direct regression test for PRE-5)
* an old-shaped payload (only the original 7 fields) still validates, with defaults
* `SchemeBundle.schemes[0]` carries the new fields
* FastAPI `TestClient` hit on `/api/schemes/PM_KISAN/requirements` → 200 with the
  documented shape; unknown id → 404

**Expected outcome.** The API carries documents, timeline, and evidence.

---

## Phase 9 — Frontend

**Goal.** Surface the new information inside the existing Dashboard, matching the
existing design language.

### 9a. `frontend/src/types/scheme.ts` — new file

The codebase currently types recommendations as `any`. Introduce narrow types for
the new data only; do not attempt to type the whole farmer object.

```ts
export type RequirementKind = "mandatory" | "conditional" | "unknown";
export type TimelineStateKind =
  | "open" | "closing_soon" | "expired" | "open_ended"
  | "unknown" | "unknown_with_mention";

export interface RequiredDocumentItem {
  raw_text: string;
  display_name: string;
  doc_type: string;
  requirement: RequirementKind;
  condition_text: string | null;
  match_confidence: "high" | "low" | "none";
  links: string[];
}

export interface RequiredDocuments {
  status: "available" | "unavailable" | "fetch_failed" | "not_fetched";
  source?: string | null;
  source_url?: string | null;
  fetched_at?: string | null;
  items: RequiredDocumentItem[];
  item_count: number;
  unmatched_count: number;
  extractor_version: number;
}

export interface MatchSignal { /* §5.6 */ }
export interface ApplicationTimeline { /* §5.2 */ }
export interface TimelineState {
  state: TimelineStateKind;
  days_remaining: number | null;
  label: string;
}
```

### 9b. `frontend/src/components/SchemeReasonPanel.tsx` — new

Props: `{ reasonSummary: string; signals: MatchSignal[]; confidence: string }`

* Renders the existing "Why you were selected" block style verbatim
  (`bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border`), so it drops into the
  current card without visual disruption.
* `reason_summary` as the lead sentence in `font-medium`.
* Each signal as a row with `<CheckCircle2 className="w-4 h-4 text-emerald-500" />`
  + `signal.text` — reuse the exact markup already at `Dashboard.tsx:496`.
* Confidence chip using the existing `<Badge variant="outline">`:
  `verified` → emerald + "Verified criteria";
  `high` → emerald-subtle + "High confidence";
  `medium` → amber + "Medium confidence";
  `low` → slate + "Low confidence — verify on the official page".
* When `confidence === "low"`, render a one-line note:
  *"These criteria were extracted automatically from the official scheme page.
  Please confirm on myScheme before applying."* — with the source link.
  **This is not optional.** See §12.

### 9c. `frontend/src/components/SchemeDocumentsList.tsx` — new

Props: `{ documents: RequiredDocuments | null; sourceUrl?: string | null }`

| `documents.status` | Render |
|---|---|
| `"available"` | header `Documents Required ({item_count})`; first 5 items; a `Show all N` text button toggling local `useState` (no new dependency — the codebase has no accordion component); each item `display_name`, with `condition_text` as a small amber `<Badge>If applicable</Badge>`; `links[]` as an external `<a target="_blank" rel="noopener noreferrer">`; a footer line `Source: myScheme.gov.in` linking `sourceUrl` |
| `"unavailable"` | `Document list not published on myScheme for this scheme.` + `Check the official page →` |
| `"fetch_failed"` | `Document list temporarily unavailable.` |
| `"not_fetched"` / `null` | render **nothing** (no empty box) |

`doc_type` selects a `lucide-react` icon (`FileText` default, `CreditCard` for
`AADHAAR`/`PAN`, `MapPin` for address/domicile, `Sprout` for `LAND_RECORD`,
`GraduationCap` for `EDUCATION_CERTIFICATE`) — all already imported in `Dashboard.tsx`.
**The label text is always `display_name`, never a prettified `doc_type`.**

### 9d. `frontend/src/components/SchemeTimelineBadge.tsx` — new

Props: `{ timelineState: TimelineState | null; timeline: ApplicationTimeline | null }`

| `state` | Badge |
|---|---|
| `open` | emerald, `<CheckCircle2 />` + label |
| `closing_soon` | amber, `<AlertTriangle />` + label |
| `expired` | rose, `<XCircle />` + label, **card dims to `opacity-70` and the Apply button reads `View scheme` instead of `Apply`** |
| `open_ended` | slate, `<Info />` + label |
| `unknown` | slate-subtle, `<Info />` + `Application deadline not published` |
| `unknown_with_mention` | amber-subtle + label; on click/expand shows the verbatim `text_mentions[].excerpt` inside a `<blockquote>` with the caption *"Quoted from the official scheme page"* |

Also renders `application_modes[]` as small chips (`Online`, `Offline`, `Online - via CSC`),
linking `url` when present.

### 9e. `frontend/src/pages/Dashboard.tsx` — modify

Two insertion points, both inside the `schemeTab === 'eligible'` branch:

1. **Bundle scheme card** — currently `Dashboard.tsx:~490-520`. After the existing
   "Why you were selected" block, insert:
   ```tsx
   <SchemeReasonPanel reasonSummary={scheme.reason_summary}
                      signals={scheme.match_signals || []}
                      confidence={scheme.reason_confidence} />
   <SchemeTimelineBadge timelineState={scheme.timeline_state}
                        timeline={scheme.application_timeline} />
   <SchemeDocumentsList documents={scheme.required_documents}
                        sourceUrl={scheme.source_url} />
   ```
   Replace the existing raw `scheme.explanation` map with `SchemeReasonPanel` only
   if `scheme.match_signals?.length` — otherwise keep the existing render, so a
   pre-enrichment backend still works.

2. **Fallback individual-scheme card** — `Dashboard.tsx:~538-580`. Same three
   components, in a compact variant.

Also update both `Apply` buttons: prefer `scheme.source_url` (now actually
delivered), keep the existing slug-guess fallback.

**Information hierarchy per card** (top → bottom):
```
Scheme name + % match badge
Timeline badge (open / closing soon / expired / unknown)
Why recommended  (reason_summary + signals + confidence)
Predicted impact (existing block, unchanged)
Documents required (collapsed to 5)
Apply / View scheme + Source: myScheme.gov.in
```

**Responsive.** Reuse the existing `flex flex-col md:flex-row` pattern already on the
card. The document list is a single column on mobile.

**Accessibility.** The Show-all toggle is a real `<button>` with `aria-expanded`.
Status is never conveyed by colour alone — every badge carries its icon and text.

### 9f. `frontend/src/i18n/locales/{en,hi,mr,gu}.json`

Add under `dashboard`:
```
"why_recommended", "documents_required", "documents_show_all",
"documents_unavailable", "documents_failed", "deadline_unknown",
"deadline_open_ended", "deadline_closed", "deadline_closing_soon",
"confidence_verified", "confidence_high", "confidence_medium",
"confidence_low", "confidence_low_note", "source_myscheme",
"view_scheme", "quoted_from_official_page", "if_applicable"
```
English text as specified above. For `hi`/`mr`/`gu`, add the **same keys with the
English strings as placeholders** — the repo already ships partial translations, and
a missing key falls back to the key name, which is worse than English.

**Signal `text` strings themselves are generated server-side in English and are NOT
translated.** Note this as a known limitation; translating them would require moving
sentence assembly to the client, which is a separate piece of work.

**Dependencies.** Phase 8.

**Validation.** `cd frontend && npm run lint && npm run build`, then `npm run dev`
and confirm a real farmer's dashboard shows documents, a timeline badge, and reasons.

**Expected outcome.** Feature visible end-to-end.

---

## Phase 10 — Regression & end-to-end tests

**File:** `backend/tests/test_regression.py`

* `RulesEngine.check_scheme` output for a fixed scheme+profile pair is byte-identical
  to a committed golden fixture (proves eligibility logic is untouched)
* `SchemeExplainer.explain_eligible` / `explain_ineligible` produce the same strings
  as before (the Dashboard still renders them)
* `rank_schemes` `relevance_score` for a fixed input is unchanged to 6 dp
- `get_published_schemes` projection includes every field read by
  `_classify_domain`, `SchemeSuccessPredictor.build_scheme_features`,
  `BenefitPredictor.predict_benefit`, `SchemeKnowledgeGraph._build_base_graph`, and
  the ranking loop — **assert this with an explicit field-name list**, not by eyeball
* `MySchemeNormalizer.normalize` still produces every pre-existing key

**File:** `backend/tests/test_e2e_recommendations.py`

Full path with `respx`-mocked myScheme and a seeded fake db:

1. ingest 3 schemes (one with documents + close date, one with documents + no dates,
   one with no documents at all)
2. build a farmer profile that matches scheme 1 and 2
3. call `RecommendationService.get_recommendations`
4. assert: scheme 1 → `timeline_state.state == "expired"` (close date 2025-03-31),
   documents present, ≥ 2 match signals, `reason_summary` non-empty;
   scheme 2 → `timeline_state.state in {"open_ended","unknown"}`;
   scheme 3 → `required_documents.status == "unavailable"` and the UI contract holds
   (`items == []`)
5. assert no scheme carries a `close_date` that was not in the mocked source
   (**anti-fabrication assertion — make this explicit**)

Source-failure scenarios:
* `/documents` returns 500 → ingestion completes, `status == "fetch_failed"`,
  everything else persists
* `/schemes/v6/public/schemes` returns 500 → cycle logs an error, no partial writes
* `/search/v6/schemes` returns 403 → `run_ingestion_cycle` returns `errors: 1` and
  writes an ingestion log row (existing behaviour — assert it still holds)

---

# PART V — CROSS-CUTTING

## 10. Failure modes (Phase 12) — required behaviour

| Failure | Required behaviour |
|---|---|
| Source API unavailable (`/search` 403/5xx) | `run_ingestion_cycle` returns `errors: 1`, writes an ingestion log row, **no partial writes**. Existing enrichment untouched. Recommendations keep serving stored data. |
| `/documents` 5xx or timeout for one scheme | `status = "fetch_failed"`; a previously-stored `available` record is **preserved**; `stats["documents_failed"]` increments; the cycle continues. |
| `/documents` returns `data: null` | `status = "unavailable"`, `items: []`. UI says *"Document list not published on myScheme."* |
| Source changes schema (`documents_required` key renamed) | AST flatten yields 0 items, markdown parse yields 0 items → `status = "unavailable"`. **No crash, no fabrication.** Detect via the `documents_missing` counter jumping in `scheme_ingestion_log`. |
| Missing deadline (99 % of schemes) | `timeline.status = "unknown"`; UI shows *"Application deadline not published"*. Never a guessed date. |
| Malformed date (`"24/02/2019"`, `"NA"`) | `close_date = None`, `close_date_raw` preserved verbatim, `unparseable_date` mention added, `status` degrades to `unknown`. |
| Expired deadline | Computed at read time in IST. Card dims, badge is rose, Apply → `View scheme`. The scheme is **not** removed from recommendations — an expired scheme may reopen and the user still benefits from knowing about it. |
| Conflicting dates (`close < open`) | `status = "unknown"`, both raws kept, `conflicting_dates` mention. |
| Multiple deadlines | The source has none. If a future source change introduces them, `application_timeline.status` stays `unknown` and each is recorded as a verbatim `text_mentions` entry. **Do not invent a multi-window model for data that does not exist.** |
| Conditional documents | `requirement = "conditional"` with verbatim `condition_text`. UI shows an amber "If applicable" badge. Never silently promoted to mandatory. |
| Duplicate documents | De-duplicated by case-folded `raw_text`, first-seen order preserved. |
| Incomplete eligibility criteria (`rules == []`) | Scheme is already excluded by `RulesEngine.check_scheme` (`status != published or no rules` → ineligible). Unchanged. |
| Partial user profile (`state` is `None`) | `RulesEngine` already treats a `None` profile value as a failed rule. Scheme becomes ineligible; no signal is produced for it. **Never emit a signal for a rule the user did not actually satisfy.** |
| Zero match signals on an eligible scheme | `reason_summary` = the documented no-signal sentence; `reason_confidence = "low"`; UI shows the low-confidence note. |
| Enrichment failure mid-backfill | Script is resumable — the selection query naturally re-picks unenriched rows. |
| Stale enrichment | `required_documents.fetched_at`. Surface staleness only via `scheme_ingestion_log`; do not show a "stale" badge to farmers (the underlying facts change rarely and a stale badge would erode trust in correct data). |
| Source scheme removed | Existing behaviour: the doc simply stops being refreshed. `last_fetched` ages. Out of scope. |
| Scheme updated after recommendation | Recommendations are computed fresh on every request (no cache exists), so the next page load reflects the change. `scheme_change_events` + `notifications` already fire — now also for `documents` and `timeline` changes. |
| Stale recommendation cache | **There is no cache.** Do not add one — `CLAUDE.md` explicitly says this is a known limitation, not a bug to fix unasked. |
| Migration/backfill failure | Nothing is deleted; the script only `$set`s new fields. Rollback = `$unset required_documents, application_timeline`. |

## 11. Security, reliability, data quality (Phase 13)

* **Source validation.** Every payload access uses `.get()` with defaults; no
  `KeyError` path exists. Item cap of 40. String length cap of 500 chars per
  `raw_text` (truncate with `…`, and note the truncation in the item).
* **Sanitization / injection.** Document text is rendered by React as **text
  children**, never `dangerouslySetInnerHTML`. Markdown links are extracted into a
  typed `links[]` array; before rendering an `<a href>`, assert the URL starts with
  `http://` or `https://` — drop `javascript:` / `data:` URIs. Do this check on both
  the backend (extractor) and the frontend (component). NoSQL injection is not a
  risk: all values are `$set` as literals, never used as query operators.
* **Rate limiting / politeness.** One extra HTTP call per *newly fetched* scheme
  (schemes fresh within 24 h are skipped and cost nothing). Reuses the existing
  `max_concurrency=2` + 0.5 s sleep + 5-retry exponential backoff.
* **Idempotency.** Enrichment is a pure function of the payload; writes are `$set`
  on whole sub-documents. Re-running never duplicates or appends.
* **Transaction boundaries.** MongoDB standalone — no multi-document transactions.
  Each scheme is a single `update_one`, which is atomic at the document level. That
  is sufficient because enrichment is 1:1 with the scheme document. This is a
  deliberate reason to embed rather than use a side collection.
* **Concurrency.** The daily loop and a manual `POST /api/monitoring/refresh-schemes`
  can overlap. Both write the same derived value from the same source, so the
  outcome is the same regardless of ordering. Backfill uses `--force` off by default
  so it will not fight a concurrent ingestion.
* **Auditability.** `raw_markdown` + `*_date_raw` + `*_source` + `extractor_version`
  make every displayed fact traceable to a source string and to the code version
  that derived it. `GET /api/schemes/{id}/requirements` exposes the full record for
  manual audit.
* **Schema versioning.** `extractor_version` on both sub-documents. Bumping it makes
  the backfill script re-derive automatically — without re-fetching, if you add an
  `--offline-rederive` path.
* **Correctness posture.** This feature shows government information. Three hard
  rules, enforced in tests: (1) `raw_text` is always the displayed label;
  (2) no date is ever produced that was not a literal `YYYY-MM-DD` in the source;
  (3) no match signal is produced for a rule the profile did not pass.

## 12. The single biggest risk — read this before writing code

`extraction_method` is `"heuristic"` for **4,732 of 4,788** schemes and `"llm"` for
**zero**. The heuristics in `rule_extractor.py` produce provably wrong rules.
Verified from the live database:

| Scheme | Wrong rule | Why |
|---|---|---|
| `post-st` — *Post Matric Scholarship for **Scheduled Tribe*** | `category == "SC"` | the regex `\b(scheduled caste\|sc)\b` fires on "…**sc**holarship" style tokens and on "SC/ST" mentions |
| `post-st` | `gender == "female"` | the word "girl"/"women" appears somewhere in the text |
| `kbpyy` — Krishak Bakri Palan Yojna | `gender == "female"` | extracted from *"At least 30 percent beneficiaries should be women"* — a **preference**, not a requirement |
| `syss` — Skilled Youth Startup Scheme | `occupation_type == "government_employee"` | extracted from *"If the applicant is a child of a Government employee…"* |

Today these errors are invisible — the UI shows a terse
`"Matches: Category: Sc, State: Sikkim"`. **This feature makes them loud**, because
it renders a confident full sentence: *"Recommended because the scheme targets the
SC category, matching your profile."*

**Mitigations, all mandatory:**

1. `reason_confidence` is computed and **always rendered**. `heuristic` extraction
   with < 3 signals can never exceed `"medium"`.
2. The low-confidence note in §9b is not optional.
3. Every card links `source_url` to the official myScheme page.
4. `rule_provenance` is carried on every signal so a support/audit query can find
   every claim traceable to a heuristic rule:
   `db.schemes.find({extraction_method: "heuristic", "rules.field": "gender"})`.
5. `manually_verified: true` schemes (147 today) render as `"verified"` — giving the
   team a clear path to upgrade trust scheme-by-scheme.

**Do not attempt to fix `rule_extractor.py` in this feature.** It is a separate,
larger piece of work. Flag it, surface confidence honestly, and move on.

## 13. Performance (Phase 14)

| Dimension | Impact |
|---|---|
| Ingestion time | +1 HTTP call per newly-fetched scheme. Full catalog refresh 35 min → **≈ 70 min**. Runs once daily, off the request path. Steady state (most schemes fresh < 24 h) is near-zero. |
| Source API volume | +1 request per newly-fetched scheme. Same concurrency (2) and 0.5 s delay. |
| Database size | +1.5–2 KB/scheme → 11.5 MB → **≈ 20 MB**. Trivial. |
| Scheme fetch on the hot path | The `SCHEME_PROJECTION` in Phase 8b **removes** `eligibility_raw`/`benefits_raw` (the two largest fields) and adds the enrichment. Net: roughly flat or slightly smaller. The new `ix_status_slug` index turns the current full collection scan into an index scan. |
| Recommendation latency | Signal building is pure dict work over ~114 eligible schemes — sub-millisecond. Enrichment is read from the already-fetched document; **zero extra queries**. Measured baseline is 19.0 s, dominated by model loading and 4,774-scheme rule evaluation, neither of which this feature touches. |
| API payload | Measured baseline 1.63 MB (of which `ineligible_schemes` is 1.43 MB). This feature adds **≈ 190 KB** — kept there by `match_signals[:6]`, the `raw_markdown` strip, and the absolute rule that enrichment is **never** attached to ineligible schemes. |
| Frontend rendering | 5 documents rendered per card by default. No new dependency. |

**Not done, deliberately:** no Redis, no recommendation cache, no precomputation.
`CLAUDE.md` explicitly says the recompute-per-request behaviour is a known
limitation and not to "fix" it unasked.

## 14. Migration & rollout (Phase 18)

| Question | Answer |
|---|---|
| Do existing schemes need backfilling? | Yes — all 4,788. Without it every card shows "not published" for a month (schemes are only re-fetched when stale). |
| Can enrichment be lazy? | No. Lazy = an HTTP call to a government API inside a user request. Rejected. |
| Is a migration required? | No schema migration — MongoDB is schemaless and every new field is optional with a default. Only a data backfill. |
| Is re-ingestion sufficient? | Functionally yes, but it re-runs Gemini rule extraction for every scheme (cost + 35 min + risk of rewriting `rules[]`). The backfill script is narrower and safer. |
| Should enrichment be rerun? | Only when `extractor_version` is bumped or `--force` is passed. |
| How are failures retried? | The backfill selection query re-picks `fetch_failed` rows; just re-run it. The daily ingestion also retries naturally. |
| How do we avoid breaking current recommendations? | Every change is additive. Phases 1–6 write data nothing reads. Phase 7 adds response keys. Phase 8 adds model fields with defaults. Phase 9 renders conditionally on the new fields being present. |

**Rollout order**
1. Deploy Phases 1–5 (code only; new ingestion cycles start enriching). Verify the
   next daily cycle's `scheme_ingestion_log` shows `documents_fetched > 0`.
2. Run `backfill_scheme_enrichment.py --limit 50` off-peak. Spot-check 5 schemes
   against their myScheme pages **by eye**.
3. Run the full backfill (~36 min). Verify the index list.
4. Deploy Phases 7–8. `GET /api/farmers/me` now carries the new keys; old frontends
   ignore them.
5. Deploy Phase 9.

**Rollback**
* Frontend: revert Phase 9 — the backend is a superset and stays compatible.
* Backend: revert Phases 7–8; the stored enrichment is inert.
* Data: `db.schemes.updateMany({}, {$unset: {required_documents: "",
  application_timeline: "", myscheme_object_id: "", scheme_open_date_raw: "",
  scheme_close_date_raw: ""}})`. No existing field is ever modified, so rollback is
  lossless.

---

# PART VI — DECISION SUMMARY

## A. Current architecture

FastAPI modular monolith + MongoDB (motor) + React 19 SPA. A background asyncio
loop ingests all ~4,772 myScheme.gov.in schemes daily through
`fetcher → parser → normalizer → rule_extractor → scheduler`, storing free-text
eligibility and heuristically-derived `rules[]`. On every `GET /api/farmers/me` the
server loads all 4,774 published schemes, runs a YAML-less rules engine, mock ML
scoring, and a NetworkX MWIS bundler, and returns eligible + ineligible lists with
one-line explanation strings.

## B. Problem

Recommended schemes tell the farmer nothing actionable: no required documents
(the data exists at source on an endpoint we never call), no application dates
(parsed by `parser.py`, silently dropped by `normalizer.py`), and a terse
`"Matches: State: Maharashtra"` string with no structured evidence, no confidence,
and no provenance.

## C. Recommended architecture

Extend the existing ingestion pipeline with a dedicated, idempotent enrichment
stage. Two new pure modules derive typed document requirements and a conservative
application timeline from verbatim source data; both are embedded 1:1 in the scheme
document with full provenance. The recommendation engine converts the
already-computed `passed_rules` into typed match signals and a deterministically
assembled reason sentence with an honest confidence grade. **No LLM is added.**
A one-shot backfill script plus four indexes bring the existing 4,788 rows up to
date.

## D. Data flow

```
myScheme /search/v6/schemes ──┐
myScheme /schemes/v6/public/schemes?slug= ──┤
myScheme /schemes/v6/public/schemes/{objectId}/documents ──┘   ← NEW
        │
        ▼  fetcher.py (+fetch_scheme_documents, +fetch_documents_batch)
        ▼  parser.py  (+myscheme_object_id, +application_modes, +parse_documents)
        ▼  document_extractor.py + document_taxonomy.py   ← NEW
        ▼  timeline_extractor.py                          ← NEW
        ▼  normalizer.py (+application_timeline, +raw dates, +object id)
        ▼  scheduler.py  (fetch → build → manually_verified guard → $set → change events)
        ▼
   MongoDB schemes.{required_documents, application_timeline}
        ▼  farmers.py get_published_schemes  (SCHEME_PROJECTION + ix_status_slug)
        ▼  rules_engine.py  → passed_rules[]  (unchanged)
        ▼  scheme_explainer.py  build_match_signals / build_reason_summary / confidence  ← NEW
        ▼  ranking_engine.py  (+6 keys on eligible results only)
        ▼  models/farmer.py  SchemeRecommendation (+7 fields — else silently stripped)
        ▼  GET /api/farmers/me   +   GET /api/schemes/{id}/requirements   ← NEW
        ▼  Dashboard.tsx + SchemeReasonPanel / SchemeDocumentsList / SchemeTimelineBadge
```

## E. File change map

| File | Change | Reason | Depends on |
|---|---|---|---|
| `backend/requirements-dev.txt` | **create** | pytest/respx — none installed today | — |
| `backend/pytest.ini` | **create** | test config | — |
| `backend/tests/conftest.py` | **create** | verbatim myScheme payload fixtures | — |
| `backend/app/services/crawler/document_taxonomy.py` | **create** | closed document-type vocabulary, mirrors `document_processing/normalizer.py` | — |
| `backend/app/services/crawler/document_extractor.py` | **create** | payload → typed `required_documents` | taxonomy |
| `backend/app/services/crawler/timeline_extractor.py` | **create** | dates → conservative `application_timeline` | — |
| `backend/app/services/crawler/fetcher.py` | **modify** — add `fetch_scheme_documents`, `fetch_documents_batch` | new `/documents` sub-resource | — |
| `backend/app/services/crawler/parser.py` | **modify** — `parse_detail` returns `myscheme_object_id`, `application_modes`; add `parse_documents` | the ObjectId is required to call `/documents` (PRE-6) | — |
| `backend/app/services/crawler/normalizer.py` | **modify** — carry raw dates + object id, build `application_timeline` | PRE-3: these were parsed then dropped | timeline_extractor |
| `backend/app/services/crawler/scheduler.py` | **modify** — Step 3b, enrichment attach, `manually_verified` guard, diff, stats | persist enrichment idempotently | fetcher, parser, extractors |
| `backend/scripts/backfill_scheme_enrichment.py` | **create** | enrich 4,788 existing rows + create 4 indexes | all crawler modules |
| `backend/app/ml/explainability/scheme_explainer.py` | **modify** — add `build_match_signals`, `build_reason_summary`, `compute_reason_confidence`; **keep existing methods** | structured evidence; Dashboard still renders `explanation` | — |
| `backend/app/ml/inference/ranking_engine.py` | **modify** — 6 new keys on eligible results only; add `_public_documents` | attach evidence + enrichment | explainer, timeline_extractor |
| `backend/app/models/farmer.py` | **modify** — add 7 models, extend `SchemeRecommendation`, add `datetime`/`Any` imports | **without this the fields are silently dropped (PRE-5)** | — |
| `backend/app/api/farmers.py` | **modify** — `import datetime` (PRE-1 fix), `SCHEME_PROJECTION` | fix a NameError; keep payload flat | models |
| `backend/app/api/schemes.py` | **modify** — add `GET /{scheme_id}/requirements` | full record incl. `raw_markdown` for the detail view and audit | models |
| `frontend/src/types/scheme.ts` | **create** | type the new payload | — |
| `frontend/src/components/SchemeReasonPanel.tsx` | **create** | why-recommended + confidence | types |
| `frontend/src/components/SchemeDocumentsList.tsx` | **create** | documents with states | types |
| `frontend/src/components/SchemeTimelineBadge.tsx` | **create** | timeline states | types |
| `frontend/src/pages/Dashboard.tsx` | **modify** — 2 insertion points in the eligible tab; Apply uses `source_url` | the only recommendation UI | components |
| `frontend/src/i18n/locales/{en,hi,mr,gu}.json` | **modify** — ~18 new `dashboard.*` keys | i18n is already wired | — |

## F. Database change map

| Model/Table | Change | Fields | Reason |
|---|---|---|---|
| `schemes` | add embedded doc | `required_documents` (§5.1) | documents come from a 1:1 sub-resource; read on the same hot query |
| `schemes` | add embedded doc | `application_timeline` (§5.2) | dates + application modes + verbatim mentions |
| `schemes` | add scalar | `myscheme_object_id: str \| null` | the key required by `/documents`, `/faqs`, `/applicationchannel` |
| `schemes` | add scalar | `scheme_open_date_raw: str \| null` | verbatim `basicDetails.schemeOpenDate` (PRE-3) |
| `schemes` | add scalar | `scheme_close_date_raw: str \| null` | verbatim search `schemeCloseDate` (PRE-3) |
| `schemes` | add index | `ix_status_slug {status:1, myscheme_slug:1}` | the recommendation query is currently a full scan |
| `schemes` | add index | `ix_slug {myscheme_slug:1}` | ingestion freshness lookup, once per scheme per cycle |
| `schemes` | add index | `ix_object_id {myscheme_object_id:1}` sparse | backfill resume |
| `schemes` | add index | `ix_scheme_id {scheme_id:1}` | `GET /api/schemes/{id}` and `/requirements` |
| `scheme_ingestion_log` | add fields | `documents_fetched`, `documents_missing`, `documents_failed` | observability; detects a source schema change |
| `scheme_change_events` | new values | `changed_fields` may now contain `"documents"`, `"timeline"` | farmers get notified when requirements change |

**No unique indexes** — 8 duplicate `scheme_id` and 9 duplicate `myscheme_slug`
groups exist; creation would fail. De-duplication is separate work.

## G. API change map

| Endpoint | Change | Purpose |
|---|---|---|
| `GET /api/farmers/me` | response only — each `recommended_schemes[]` / `recommended_bundles[].schemes[]` gains `source_url`, `match_signals`, `reason_summary`, `reason_confidence`, `required_documents`, `application_timeline`, `timeline_state` | the feature. Additive; old clients unaffected. `ineligible_schemes[]` is **unchanged** (payload). |
| `PUT /api/farmers/me` | same response shape as above | it returns fresh recommendations too |
| `GET /api/schemes/{scheme_id}/requirements` | **new** | full record incl. verbatim `raw_markdown`, for the detail dialog and for auditing what we display |
| `GET /api/schemes/` | unchanged | — |
| everything else | unchanged | — |

## H. Frontend change map

| Component/File | Change | Purpose |
|---|---|---|
| `src/types/scheme.ts` | create | types for documents / timeline / signals |
| `src/components/SchemeReasonPanel.tsx` | create | reason sentence + signal list + confidence chip + low-confidence caveat |
| `src/components/SchemeDocumentsList.tsx` | create | documents with available / unavailable / failed / absent states, show-all toggle, conditional badges, source link |
| `src/components/SchemeTimelineBadge.tsx` | create | open / closing-soon / expired / open-ended / unknown badge + application modes + verbatim excerpt |
| `src/pages/Dashboard.tsx` | modify | mount the three components in the bundle card and the fallback card; Apply uses the now-delivered `source_url`; expired cards dim and read "View scheme" |
| `src/i18n/locales/*.json` | modify | ~18 new `dashboard.*` keys |

## I. Implementation sequence

```
0.  Test harness (pytest, respx, fixtures)
1.  document_taxonomy.py                          ← no deps
2.  document_extractor.py                         ← needs 1
3.  timeline_extractor.py                         ← no deps
4.  fetcher.py + parser.py                        ← no deps (parallel with 1–3)
5.  normalizer.py + scheduler.py                  ← needs 2, 3, 4
6.  backfill script + indexes                     ← needs 5
7.  scheme_explainer.py + ranking_engine.py       ← needs 3, 6 (needs data to exist)
8.  models/farmer.py + api/farmers.py + api/schemes.py  ← needs 7
9.  frontend                                      ← needs 8
10. regression + e2e tests                        ← needs 9
```

Hard dependencies: 2←1, 5←{2,3,4}, 6←5, 7←6, 8←7, 9←8.
1, 3 and 4 may be done in parallel.

## J. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Heuristic rules are wrong (PRE-4) → confident but false reasons | **High** — false claims about government eligibility | `reason_confidence` always rendered; `heuristic` + <3 signals capped at `"medium"`; mandatory low-confidence caveat; `source_url` on every card; `rule_provenance` on every signal for auditing |
| `/documents` is undocumented and may change or be withdrawn | Medium | Every access is `.get()`-guarded → degrades to `status: "unavailable"`. `documents_missing` in `scheme_ingestion_log` is the alarm. Verbatim `raw_markdown` preserved so a parser change can re-derive without re-fetching. |
| myScheme API key rotates / 403 | Medium | Existing behaviour: cycle logs `errors: 1`, stored data keeps serving. During this audit a transient 403 was observed on the first call and 200 on retry — `_request_with_retry` already covers it. |
| Documents attached to 4,652 ineligible schemes | **High** — +8 MB per request | Absolute rule: enrichment on the eligible loop **only**. Enforced by `test_ranking_enrichment.py`. |
| New fields silently dropped by `response_model` (PRE-5) | **High** — feature looks broken with no error | Phase 8a is mandatory and has a dedicated regression test |
| Backfill overwrites hand-curated data | Medium | `manually_verified` guard replicated exactly from `scheduler.py`; `--dry-run` first; updates keyed on `_id` |
| Backfill takes ~36 min and could be interrupted | Low | Fully resumable via the selection query; `--limit` for staged runs |
| Timezone off-by-one marks a live scheme expired | Medium | IST calendar-date comparison; boundary test at `days_remaining == 0` asserts **still open** |
| Duplicate `scheme_id`/`myscheme_slug` cause double writes | Low | All backfill writes keyed on `_id` |
| Ingestion time doubles (35 → 70 min) | Low | Runs daily in the background; steady state is near-zero because fresh schemes are skipped |
| Document text contains a hostile URL | Low | `http(s)`-only assertion on both backend and frontend; React text rendering only, never `dangerouslySetInnerHTML` |
| Signal sentences are English-only in a Hindi/Marathi UI | Low | Documented limitation; i18n keys cover the chrome. Moving sentence assembly client-side is separate work. |

## K. Definition of done

**Functional**
1. A recommended scheme with source documents shows them, labelled with the
   **verbatim** source text, with a `Source: myScheme.gov.in` link.
2. A recommended scheme without source documents shows *"Document list not published
   on myScheme for this scheme"* — never an empty list presented as "no documents needed".
3. A scheme with a `schemeCloseDate` shows a dated badge; if that date is past in IST
   the card dims and Apply reads "View scheme".
4. A scheme with only `schemeOpenDate` shows *"Open — no closing date published"*.
5. A scheme with neither shows *"Application deadline not published"*.
6. Every eligible scheme shows a `reason_summary` sentence naming only criteria the
   user actually satisfied, plus a confidence chip.
7. `low` confidence renders the verification caveat.
8. Bundles carry the same information as standalone cards.

**Technical**
9. `required_documents.raw_markdown` and `*_date_raw` are present in Mongo for every
   enriched scheme (provenance preserved).
10. Running the backfill twice reports 0 schemes processed on the second run.
11. Running a 5-scheme ingestion cycle twice produces byte-identical documents.
12. `GET /api/farmers/me` returns all 7 new keys on eligible schemes and **none** on
    ineligible schemes.
13. `ineligible_schemes` payload size is unchanged from the 1.43 MB baseline (±2 %).
14. `SchemeRecommendation.model_dump()` retains every new field (PRE-5 regression test).
15. All four indexes exist on `schemes`.
16. `POST /api/farmers/me/applications` no longer raises `NameError` (PRE-1).
17. `cd backend && venv/Scripts/python.exe -m pytest -q` — all green.
18. `cd frontend && npm run lint && npm run build` — clean.

**Anti-fabrication (each has an explicit test)**
19. No `close_date`/`open_date` is ever emitted that was not a literal `YYYY-MM-DD`
    in the source payload.
20. No document is ever displayed whose `raw_text` was not a literal line in the
    source payload.
21. No match signal is ever emitted for a rule that appears in `failed_rules`.
22. Every numeral appearing in a signal's `text` also appears in that signal's
    `scheme_value` or `profile_value`.

---

# INSTRUCTIONS FOR CLAUDE SONNET 5

You are implementing the feature specified above in
`C:\Users\gmore\OneDrive\Desktop\IPD_Project\ipd`. **Implement this plan exactly.**

### What to implement

Add three things to every recommended scheme: (1) required documents, (2) an
application timeline, (3) an evidence-based reason. Ingest documents from the
myScheme `/documents` sub-resource discovered in §2.2, persist enrichment on the
scheme document, derive reasons deterministically from the rules engine's existing
`passed_rules`, expose it all through the existing `/api/farmers/me` response, and
render it in `Dashboard.tsx`.

### Order

Phases 0 → 10, in order, exactly as written in Part IV. Do not skip Phase 0 — no
test tooling is installed. Do not start Phase 7 before Phase 6 has actually written
data. Phases 1, 3 and 4 have no interdependencies and may be batched.

### Files you will touch

Exactly the files in the File Change Map (§E). Nothing else.

### Architectural decisions already made — do not revisit

* Enrichment is **embedded** in the `schemes` document. Not a side collection.
* Enrichment happens at **ingestion**, never inside a user request.
* Reasoning is **100 % deterministic**. **Do not add an LLM anywhere.** Do not
  modify `rule_extractor.py`.
* Enrichment attaches to **eligible schemes only** — never to `ineligible_schemes`
  (that list is already 4,652 entries / 1.43 MB).
* Timeline expiry is computed at **read time** in **Asia/Kolkata**, never stored.
* `raw_text` is the label the user sees. `doc_type` drives icons and grouping only.
* Backfill writes are keyed on `_id`. Never on `scheme_id` or `myscheme_slug`.
* The taxonomy in Phase 1 is a **vocabulary**, not scheme-specific data. Do not add
  a scheme name, slug, or scheme-specific document list anywhere in the code.

### What NOT to change

* `backend/app/ml/rules/rules_engine.py` — eligibility logic. Read-only.
* `backend/app/services/crawler/rule_extractor.py` — known-buggy, out of scope.
* `SchemeExplainer.explain_eligible` / `explain_ineligible` / `_translate_rule` —
  the Dashboard renders `scheme.explanation` today. Add methods; change none.
* `MySchemeNormalizer.compute_content_hash` — changing it would mark all 4,788
  schemes as changed and fire 4,788 notifications.
* `IneligibleScheme` in `models/farmer.py`.
* The ineligible branch of `rank_schemes`.
* `backend/app/document_processing/**` — the OCR/Vision IDP pipeline is unrelated.
* Anything in `backend/app/ml/ocr/**` (legacy).
* Do **not** add a recommendation cache, Redis, or precomputation. `CLAUDE.md`
  says the recompute-per-request behaviour is a known limitation, not a bug to fix.
* Do **not** create unique indexes — duplicates exist and creation will fail.
* Do **not** add pytest/respx to `backend/requirements.txt`; use `requirements-dev.txt`.

### Prohibited assumptions

* Do **not** assume the myScheme detail endpoint contains documents. It does not —
  they are on `/schemes/v6/public/schemes/{objectId}/documents`.
* Do **not** assume the search result's `item.id` is the ObjectId. It is an
  Elasticsearch id. The ObjectId is `detail["data"]["_id"]`.
* Do **not** assume `documentsRequired_md` is always present. Sometimes only the
  `documents_required` AST is; sometimes only the markdown. Handle both.
* Do **not** assume most schemes have a deadline. **0.5 %** have a close date.
  "Unknown" is the normal case and must look deliberate in the UI, not broken.
* Do **not** parse a date out of free text. Ever.
* Do **not** assume a field added to a dict in `ranking_engine.py` reaches the
  client — `response_model` strips undeclared fields (verified).
* Do **not** assume `datetime` is imported in `backend/app/api/farmers.py`. It is not.
* Do **not** assume a test suite exists. There is none.
* Do **not** assume `requirements.txt` still has a merge conflict — `CLAUDE.md` is
  stale on that point; it is resolved.
* Do **not** invent a multi-window or recurring-deadline model. The source has no
  such data.

### What must be tested

Every test listed per phase, plus §K.19–22 (the anti-fabrication assertions).
At minimum: taxonomy classification, document extraction incl. malformed/escaped/
link-bearing input and idempotency, date parsing incl. the IST boundary and
conflicting dates, signal generation and ordering, confidence computation, response-model
field retention, ingestion idempotency, `manually_verified` protection, backfill
resumability, the full e2e path, and regression proof that eligibility scores and
explanation strings are unchanged.

### Edge cases that must work

Documents absent · documents fetch fails (previous good data preserved) ·
AST-only payload · markdown-only payload · run-on `1. [A](u)1. [B](u)` lists ·
double-HTML-escaped text · duplicate document lines · `(If applicable)` conditionals ·
no dates · open date only · close date only · close before open · unparseable date ·
close date exactly today in IST (**still open**) · zero match signals ·
partial profile (`state` is `None`) · `manually_verified` scheme ·
scheme with `myscheme_slug: null` (the 9 YAML-seeded rows) · source API 403/500 ·
duplicate `scheme_id` rows.

### Completion

Done when every item in §K "Definition of done" (1–22) is verifiably true, `pytest`
is green, `npm run build` is clean, and a real farmer's dashboard shows documents,
a timeline badge, and an evidence-based reason for at least one recommended scheme —
with every unavailable field stating honestly that the information is not published,
rather than showing a fabricated value or an empty box.

### If you find a problem with this plan

Say so in one or two sentences, state your assumption, and keep implementing.
Do not silently deviate, and do not stop and wait.
