# AgriSense Memory Bank
> Permanent AI Knowledge Base | Team: Binary Brains | Created: 2026-07-21

---

## What Is This?

This `memory-bank/` folder is the **permanent source of truth** for this project. It replaces the need to re-analyze the entire repository at the start of every AI session.

**Before doing anything** in a new session, read these files in order:
1. `PROJECT_CONTEXT.md` — understand the project
2. `ARCHITECTURE.md` — understand the system
3. `SESSION_STATE.md` — understand where work left off

---

## Files in This Directory

| File | Purpose | When to Read | When to Update |
|---|---|---|---|
| `PROJECT_CONTEXT.md` | Complete project overview, stack, workflows | Every new session | When major feature added, tech stack changes |
| `ARCHITECTURE.md` | System design, module map, data flows | When working on system structure | When adding modules, routes, or patterns |
| `API_REFERENCE.md` | All REST API endpoints documented | When adding/changing APIs | On every API change |
| `DATABASE.md` | MongoDB collections, schemas, relationships | When working on data models | When schema changes |
| `OCR_PIPELINE.md` | 7-stage OCR system in detail | When working on document processing | When OCR pipeline changes |
| `FEATURES.md` | All 10 features documented with files, APIs, flows | When working on a specific feature | When feature behavior changes |
| `DECISIONS.md` | Engineering decisions with rationale | When making architectural choices | When a significant design decision is made |
| `KNOWN_ISSUES.md` | Active bugs, debt, and limitations | When debugging or planning | When bugs are found or fixed |
| `TODO.md` | Prioritized task backlog | When planning work | When tasks are completed or added |
| `CHANGELOG.md` | Development history | When needing historical context | After every code change session |
| `SESSION_STATE.md` | Current work state, critical context | Every new session | At end of every session |

---

## Critical Rules for AI Engineers

1. **Read Memory Bank first** — before touching any code
2. **Verify against live code** — Memory Bank can be stale
3. **Update Memory Bank after every change** — don't let it drift
4. **The OCR entry point is ONLY `pipeline.py:process()`**
5. **Recommendations are computed on every `GET /me` — not stored**
6. **Login uses form-encoded body (OAuth2), not JSON** — frontend uses `username` = email
7. **All DB calls must use `await`** — Motor is async
8. **`profile_wizard_complete`** is the dashboard access gate
9. **Pydantic v2**: use `.model_dump()` not `.dict()`, `@field_validator` not `@validator`
10. **Tesseract is a system binary** — must be installed on host OS, not pip-installable

---

## Quick Reference: Start Commands

```bash
# Backend
cd backend
uvicorn app.main:app --reload
# → http://localhost:8000
# → Swagger: http://localhost:8000/docs

# Frontend
cd frontend
npm run dev
# → http://localhost:5173

# MongoDB (if not running)
mongod --dbpath /usr/local/var/mongodb
# OR: brew services start mongodb-community

# OCR Health Check
curl http://localhost:8000/api/monitoring/ocr-health
```

---

## Quick Reference: Key File Paths

### Backend Entry Points
| Purpose | File |
|---|---|
| App config | `backend/app/main.py` |
| Security / JWT | `backend/app/core/security.py` |
| Database connection | `backend/app/core/database.py` |
| Farmer profile model | `backend/app/models/farmer.py` |
| OCR pipeline | `backend/app/ml/ocr/pipeline.py` |
| Scheme recommendations | `backend/app/ml/services/recommendation_service.py` |
| Scheme rules | `backend/app/ml/rules/schemes_rules.yaml` |
| ML models | `backend/app/ml/models/` |

### Frontend Entry Points
| Purpose | File |
|---|---|
| Router | `frontend/src/App.tsx` |
| API client | `frontend/src/lib/api.ts` |
| Auth guard | `frontend/src/components/ProtectedRoute.tsx` |
| Profile setup | `frontend/src/pages/ProfileWizard.tsx` |
| Dashboard | `frontend/src/pages/Dashboard.tsx` |
| i18n config | `frontend/src/i18n/i18n.ts` |

---

## Project at a Glance

```
AgriSense = FastAPI backend + React SPA + MongoDB + Tesseract OCR + ML Engine

Purpose: Help Indian farmers discover and apply for government welfare schemes
Problem: Millions of farmers don't know about or can't access scheme benefits
Solution:
  - Scan Aadhaar/PAN → OCR auto-fills profile
  - YAML rules + ML model ranks eligible schemes
  - Knowledge graph finds optimal non-conflicting scheme bundles
  - Multi-language UI (en/hi/mr/gu) + voice input
  - Community stories for social proof

10 features | 25+ REST endpoints | 7-stage OCR pipeline | 10 schemes | 4 languages
MongoDB: agrisense_db → farmers + stories collections
ML Models: scheme_success_model.pkl (~1MB) + crop_model.pkl (~44MB) + document_classifier.pt
```
