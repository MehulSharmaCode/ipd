# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgriSense is a FastAPI + React platform that helps Indian farmers discover government welfare schemes. Farmers upload ID documents (Aadhaar, PAN, Maharashtra 7/12 land record); an Intelligent Document Processing pipeline (Tesseract OCR + Gemini Vision) extracts and normalizes their profile; a rules engine + ML predictors + a NetworkX knowledge graph then rank eligible schemes and compute conflict-free "bundles" (Maximum Weight Independent Set).

This repo (`ipd/`) is the git root — the parent `IPD_Project/` folder is not versioned.

## Commands

### Backend (`backend/`, Python 3.10+, FastAPI)
```bash
cd backend
uvicorn app.main:app --reload      # http://localhost:8000, Swagger at /docs
pip install -r requirements.txt
```
There is no pytest suite. Ad-hoc verification scripts are run directly, e.g.:
```bash
python test_auth_api.py
python test_db2.py                 # Motor async connection check
python backend/scripts/verify_ocr.py
curl http://localhost:8000/api/monitoring/ocr-health   # OCR health check
```
Requires a system-installed Tesseract binary (not pip-installable) — path resolved in `app/ml/ocr/config.py`. Requires `backend/.env` with `MONGO_URI`, `DATABASE_NAME`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GEMINI_API_KEY`, `MYSCHEME_API_KEY`, `MYSCHEME_API_BASE`, `TESSERACT_PATH`.

**`backend/requirements.txt` currently has an unresolved git merge conflict** (`<<<<<<< HEAD` / `=======` / `>>>>>>>`) — resolve before installing.

### Frontend (`frontend/`, React 19 + Vite + TypeScript)
```bash
cd frontend
npm run dev        # http://localhost:5173 (Vite also falls back to 5174/5175)
npm run build
npm run lint        # ESLint flat config
npm run preview
```

### MongoDB
Required and must be running locally/reachable at `MONGO_URI`; connected via `motor` async client in `app/core/database.py`.

## Architecture

### Request flow
`React SPA (Axios, JWT in localStorage)` → `FastAPI routers (/api/*)` → `services/engines (IDP, rules, ML)` → `MongoDB (motor async)`.

Routers are mounted in `backend/app/main.py`: `auth`, `farmers`, `schemes`, `upload`, `stories`, `documents` (legacy), `monitoring`. On startup, `main.py`'s lifespan handler connects Mongo, seeds schemes from YAML as a fallback, and launches a background asyncio task (`app/services/crawler/scheduler.py`) that periodically ingests scheme data from myScheme.gov.in into MongoDB.

### Document Processing (IDP) pipeline — `backend/app/document_processing/`
This is the current, actively-developed pipeline (not the older `app/ml/ocr/` code — see below):
```
Upload → DocumentRouter (router.py) → Processor (OCR or Vision) → ExtractionResult (schemas.py)
       → SemanticNormalizer (normalizer.py) → DocumentValidator (validator.py) → FarmerProfileBuilder (profile_builder.py)
```
- `ocr/aadhaar.py`, `ocr/pan.py`: Tesseract-based processors for structured ID cards.
- `vision/gemini_client.py` + `vision/gemini_pipeline.py` + `vision/prompts.py`: Google Gemini 1.5 Flash Vision processor for the unstructured, Marathi-language 7/12 land record (Tesseract cannot reliably parse it).
- `DocumentProcessor` is a `typing.Protocol` — adding a new document type means implementing the protocol and registering it in `DocumentRouter`, with no changes to existing processors.
- `SemanticNormalizer` maps varied extracted strings into canonical enums (e.g. `"Well irrigation"` → `"Well"`) before anything reaches the rules engine.
- **`app/ml/ocr/` is legacy/parallel OCR code** (older Tesseract wrapper, still referenced by `app/api/documents.py`/`upload.py` in places) — check which pipeline a given route actually calls before assuming `document_processing/` is exclusively used.

### Recommendation Engine — `backend/app/ml/`
```
FarmerProfile → FeatureStore (features/feature_store.py) → RulesEngine (rules/rules_engine.py, schemes_rules.yaml)
             → SchemeSuccessPredictor + BenefitPredictor (inference/) → KnowledgeGraph MWIS bundling (graph/knowledge_graph.py)
             → SchemePolicy reinforcement re-ranking (reinforcement/policy_engine.py)
```
Orchestrated by `ml/inference/ranking_engine.py`, exposed via `ml/services/recommendation_service.py` (singleton). `schemes_rules.yaml` is the source of truth for scheme eligibility criteria and conflict lists; the LightGBM/RandomForest models under `ml/models/*.pkl` are currently mocked/synthetic, not trained on real disbursement data. The `KnowledgeGraph` models eligible schemes as nodes weighted by `predicted_value * success_probability` and mutually-exclusive schemes as edges, then computes the Maximum Weight Independent Set to produce the optimal non-conflicting scheme bundle.

**Recommendations are computed fresh on every `GET /api/farmers/me` call — never cached/stored.** This is a known perf limitation (see `memory-bank/KNOWN_ISSUES.md`), not a bug to "fix" by adding caching unless asked.

### Scheme crawler — `backend/app/services/crawler/`
Separate subsystem (`fetcher.py` → `parser.py` → `normalizer.py` → `rule_extractor.py`) that pulls live scheme data from the myScheme.gov.in API and writes it into MongoDB, logging every run to a `scheme_ingestion_log` collection. Runs as a background loop from app startup; distinct from the static `schemes_rules.yaml`.

### Auth
JWT (HS256, via `python-jose`), bcrypt password hashing (`passlib`), issued by `app/core/security.py`. `get_current_user` FastAPI dependency gates protected routes. **Login is OAuth2 form-encoded (`username`=email, `password`), not JSON** — this trips people up because signup *is* JSON.

### Frontend structure
- `src/App.tsx`: router + providers (theme, toaster).
- `src/lib/api.ts`: single Axios instance, attaches JWT from `localStorage`, and on `401` clears storage + redirects to `/auth`.
- `src/components/ProtectedRoute.tsx`: guards routes via `GET /api/farmers/me`; `profile_wizard_complete` on the farmer doc is the gate for dashboard access vs. redirect to `/profile-setup`.
- `src/pages/`: one page per major flow — `LandingPage`, `AuthPage`, `ProfileWizard` (3-step onboarding with OCR/Vision auto-fill), `Dashboard` (recommendations, bundles, predictive alerts, crop predictor), `CommunityHub` (stories feed).
- i18n via `i18next` (`src/i18n/`), currently English/Hindi/Marathi.

### Data model
MongoDB (no migrations, schema-flexible), primary collections `farmers`, `stories`, `schemes`, `scheme_ingestion_log`. `backend/app/models/models_sql.py` is a dormant SQLAlchemy/PostgreSQL schema — **not wired to anything**; the live database is Mongo via `motor`. Don't treat it as authoritative.

## Conventions & gotchas
- Pydantic v2 throughout: use `.model_dump()` not `.dict()`, `@field_validator` not `@validator`.
- All MongoDB calls are async (`motor`) — always `await` them.
- CORS origins in `main.py` are hardcoded to local Vite dev ports (5173–5175); update if the frontend port changes.
- The frontend API base URL is hardcoded in `src/lib/api.ts` (`http://127.0.0.1:8000/api`), not env-driven.
- `backend/.env` and `backend/uploads/` are gitignored; sample `login.json`/`signup.json`/`me.json`/`error.log` at repo root of `backend/` are local test artifacts, also gitignored.

## Documentation in this repo
- `memory-bank/` holds a maintained knowledge base (`ARCHITECTURE.md`, `API_REFERENCE.md`, `DATABASE.md`, `OCR_PIPELINE.md`, `FEATURES.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`, `TODO.md`) — useful for deep dives, but written 2026-07-21 and can be stale against the current `document_processing/` pipeline and crawler subsystem (added later); verify against live code for anything load-bearing.
- `MASTER_PROJECT_DOCUMENTATION.md` (repo root) is the more recent architectural writeup, including the Gemini Vision / IDP pipeline.
- `README_PROJECT_ANALYSIS.md` (repo root) is an earlier, very detailed structural/API audit — predates `document_processing/` and the crawler.
