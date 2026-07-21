# SESSION_STATE.md — Persistent Session State
> **Last Updated:** 2026-07-21 | Update this at the END of every AI session.

---

## Last Session Summary

**Date:** 2026-07-21  
**Agent:** Antigravity (Google DeepMind)  
**Task:** Complete repository analysis + Memory Bank initialization  

**What was accomplished:**
- Full repository discovered and analyzed (backend + frontend + ML + OCR + services)
- No code was modified (analysis-only session)
- Memory Bank created with 8 core files:
  - `PROJECT_CONTEXT.md` — complete project overview
  - `ARCHITECTURE.md` — system architecture with all module maps
  - `API_REFERENCE.md` — all 25+ endpoints documented
  - `DATABASE.md` — MongoDB schema, validation, access patterns
  - `OCR_PIPELINE.md` — 7-stage OCR pipeline documentation
  - `FEATURES.md` — all 10 features documented
  - `DECISIONS.md` — 15 architectural decisions with rationale
  - `KNOWN_ISSUES.md` — 24 issues catalogued by severity
  - `TODO.md` — prioritized P0-P3 task backlog
  - `CHANGELOG.md` — initial build history

**Files Viewed (in session):**
- `backend/app/main.py`
- `backend/app/core/security.py`, `config.py`, `database.py`
- `backend/app/api/auth.py`, `farmers.py`, `upload.py`, `stories.py`, `monitoring.py`, `documents.py`
- `backend/app/models/farmer.py`, `story.py`
- `backend/app/services/predictive_alert_service.py`, `scheme_monitor.py`
- `backend/app/ml/ocr/config.py`, `preprocessing.py`, `ocr_service.py`, `classification.py`, `parsers.py`, `validation.py`, `mapping.py`, `pipeline.py`
- `backend/app/ml/rules/rules_engine.py`, `schemes_rules.yaml`
- `backend/app/ml/inference/ranking_engine.py`, `success_predictor.py`, `benefit_predictor.py`, `crop_recommender.py`
- `backend/app/ml/models/registry.py`
- `backend/app/ml/graph/knowledge_graph.py`
- `backend/app/ml/features/feature_store.py`
- `backend/app/ml/services/recommendation_service.py`
- `backend/app/ml/policy_engine/policy_ingestor.py`
- `backend/app/ml/utils/profile_mapper.py`, `logger.py`
- `frontend/src/lib/api.ts`, `utils.ts`
- `frontend/src/hooks/useVoiceInput.ts`
- `frontend/src/components/ProtectedRoute.tsx`

**Files NOT yet deeply analyzed:**
- `frontend/src/pages/LandingPage.tsx` (analyzed structure only, 36KB)
- `frontend/src/pages/Dashboard.tsx` (analyzed structure only, 80KB)
- `frontend/src/pages/ProfileWizard.tsx` (analyzed structure only, 30KB)
- `frontend/src/pages/CommunityHub.tsx`
- `frontend/src/components/CreateStoryModal.tsx`
- `frontend/src/i18n/locales/*.json`
- `backend/app/ml/reinforcement/policy_engine.py`, `interaction_logger.py`
- `backend/app/ml/explainability/scheme_explainer.py`
- `backend/app/ml/preprocessing/data_cleaning.py`, `encoders.py`
- `backend/app/ml/datasets/`

---

## Current System State

### Backend
- Status: ✅ Complete and functional (for local development)
- Start command: `cd backend && uvicorn app.main:app --reload`
- Port: 8000
- MongoDB: must be running at `localhost:27017`

### Frontend
- Status: ✅ Complete and functional
- Start command: `cd frontend && npm run dev`
- Port: 5173 (Vite default)

### Tesseract OCR
- Status: Available on macOS via Homebrew (`/opt/homebrew/bin/tesseract`)
- Detection: Multi-strategy (config.py runs detection at import time)
- Health check: `GET /api/monitoring/ocr-health`

### ML Models
| Model | File | Size | Status |
|---|---|---|---|
| Scheme Success | scheme_success_model.pkl | ~1MB | Loaded at startup |
| Crop Recommender | crop_model.pkl | ~44MB | Loaded lazily (first request) |
| Document Classifier | document_classifier.pt | ~0.5MB | Available but not used in active pipeline |

---

## Critical Context for Next Session

### Things to NEVER forget:
1. **This is a hackathon project** — focus on demo quality, not production hardening
2. **OCR entry point is ONLY `pipeline.py:process()`** — do not call Tesseract from anywhere else
3. **Recommendations are NOT stored in MongoDB** — they are computed on every `GET /me`
4. **Pydantic v2 is used** — use `.model_dump()` not `.dict()`, `@field_validator` not `@validator`
5. **Motor is async** — all DB calls must use `await`; use `async def` handlers in FastAPI
6. **`profile_wizard_complete`** is the single source of truth for dashboard access
7. **Login uses OAuth2PasswordRequestForm** — frontend must send form-encoded, not JSON; `username` field = email
8. **CORS allows localhost:5173-5175** — any other origin will be blocked
9. **Tesseract MUST be installed on the host OS** — not a Python package, it's a system binary

### Active Known Issues to be Aware Of:
- `mapping.py` uses hardcoded year 2025 for age calculation (KI-008) — now wrong
- `ocr_engine.py` + `ocr_engine_v2.py` are legacy and should be ignored
- Debug print statements exist in security.py and farmers.py (log token fragments)
- Mock data in scheme_monitor.py always returned if scraping fails
- Story upvotes can go negative (KI-013)

---

## Next Recommended Actions

Based on TODO.md P0 items:
1. Fix `mapping.py` age calculation: `age = datetime.now().year - year`
2. Fix `validation.py` DOB year cap to use `datetime.now().year`
3. Remove debug print statements from `security.py` and `farmers.py`
4. Generate and set a proper `SECRET_KEY` in `.env`
5. Add Docker Compose configuration

---

## Ongoing Maintenance Rules

**The AI software engineer must:**
1. **Update `SESSION_STATE.md`** at the end of every work session
2. **Update `CHANGELOG.md`** when code is modified (format: `[version] — date | change`)
3. **Update `KNOWN_ISSUES.md`** when bugs are found or fixed
4. **Update `TODO.md`** when tasks are completed (mark `[x]`) or added
5. **Update `API_REFERENCE.md`** when new endpoints are added or existing ones change
6. **Update `DATABASE.md`** when schema changes
7. **Update `ARCHITECTURE.md`** when new modules or patterns are introduced
8. **Read all Memory Bank files at the START of every new session** (before touching code)
9. **Verify Memory Bank against codebase** — do not assume the Memory Bank is always current
10. **Never modify more than one major subsystem without updating Memory Bank first**
