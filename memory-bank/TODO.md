# TODO.md — Task Backlog
> **Last Updated:** 2026-07-21 | Prioritized by: P0 (critical) → P3 (low)
> Cross-reference: KNOWN_ISSUES.md for bug context

---

## P0 — Security / Blockers (Must fix before any public deployment)

- [ ] **[SEC]** Replace hardcoded `SECRET_KEY` in `.env` with randomly generated 32-byte hex string
- [ ] **[SEC]** Add unique MongoDB index on `farmers.email` field
- [ ] **[SEC]** Remove all `print(f"🕵️ DEBUG: ... token ...")` statements from security.py and farmers.py
- [ ] **[DEP]** Create `Dockerfile` for backend (Python 3.11, pip install, uvicorn, tesseract)
- [ ] **[DEP]** Create `docker-compose.yml` (MongoDB + backend + frontend services)
- [ ] **[CFG]** Move API base URL to Vite env variable: `VITE_API_URL` in `.env.local`
- [ ] **[CFG]** Move CORS origins to backend `.env`: `CORS_ORIGINS=http://localhost:5173`

---

## P1 — High Priority Features / Bugs

- [ ] **[BUG]** Fix hardcoded year 2025 in `ocr/mapping.py:_parse_year_to_age()` → use `datetime.now().year`
- [ ] **[BUG]** Fix hardcoded DOB year cap (2024) in `ocr/validation.py:validate_dob()` → use `datetime.now().year`
- [ ] **[BUG]** Fix story upvote count going negative (KI-013) — add `max(0, count-1)` guard
- [ ] **[PERF]** Cache scheme recommendations (Redis or MongoDB field) — don't recompute on every GET
- [ ] **[FEAT]** Add password reset via email (forgot password flow)
- [ ] **[FEAT]** Add OpenWeatherMap API integration for real predictive alerts
- [ ] **[FEAT]** Add `VITE_API_URL` environment configuration for frontend

---

## P2 — Medium Priority Improvements

- [ ] **[CLEANUP]** Delete `backend/app/ml/ocr/ocr_engine.py` and `ocr_engine_v2.py` (legacy)
- [ ] **[FEAT]** Implement PUT `/api/stories/{id}` — edit story (owner only)
- [ ] **[FEAT]** Implement DELETE `/api/stories/{id}` — delete story (owner only)
- [ ] **[FEAT]** Add pagination to `GET /api/farmers/` (skip + limit params)
- [ ] **[FEAT]** Add more schemes to `schemes_rules.yaml` (target 25+ schemes)
- [ ] **[FEAT]** Implement real government portal scheme scraping (replace mock)
- [ ] **[FEAT]** Add admin dashboard for scheme management (CRUD on YAML/DB)
- [ ] **[FEAT]** Add story image upload support (media_url field already exists)
- [ ] **[FEAT]** Implement scheme application tracking (farmer applies → tracks status)
- [ ] **[FEAT]** Replace regex PolicyIngestor with LLM (Gemini/GPT) for better constraint extraction
- [ ] **[CLEANUP]** Clean up `dump/` directory or document its contents
- [ ] **[FEAT]** Restore `is_verified` check for story posting (commented out in stories.py)
- [ ] **[PERF]** Add MongoDB indexes: `stories.upvotes`, `stories.created_at`, `stories.crop_type`, `stories.location_state`
- [ ] **[FEAT]** Add token blacklist for logout (Redis-based)

---

## P3 — Low Priority / Nice-to-Have

- [ ] **[FEAT]** Add more Indian languages (Tamil, Telugu, Kannada, Bengali)
- [ ] **[FEAT]** Build React Native / Flutter mobile app
- [ ] **[FEAT]** Add government API integration for real application status tracking
- [ ] **[FEAT]** Implement notifications for scheme deadlines (in-app or push)
- [ ] **[UX]** Add `prefers-reduced-motion` support for 3D animations (LandingPage)
- [ ] **[FEAT]** Add farmer profile picture upload
- [ ] **[FEAT]** Add scheme application history timeline per farmer
- [ ] **[FEAT]** Implement more states in `predictive_alert_service.py` (beyond Maharashtra + Punjab)
- [ ] **[FEAT]** Add more crops to alert heuristics
- [ ] **[FEAT]** Add RL feedback loop (farmer rates recommendation → model updates)
- [ ] **[FEAT]** Internationalize OCR error messages (currently English-only)
- [ ] **[FEAT]** Add multilingual Tesseract support (Hindi/Devanagari OCR for Aadhaar cards)
- [ ] **[FEAT]** Add scheme comparison view (side-by-side)
- [ ] **[FEAT]** Add scheme deadline calendar view
- [ ] **[TEST]** Add unit tests for OCR pipeline stages
- [ ] **[TEST]** Add unit tests for rules engine (each scheme rule)
- [ ] **[TEST]** Add unit tests for benefit predictor
- [ ] **[TEST]** Add integration tests for auth flow
- [ ] **[TEST]** Add integration tests for upload + OCR
- [ ] **[TEST]** Add frontend component tests (Vitest + React Testing Library)
- [ ] **[CI]** Set up GitHub Actions: lint, test, build
- [ ] **[DOCS]** Add OpenAPI schema examples to all endpoints (FastAPI response_model + examples)
- [ ] **[DOCS]** Add JSDoc to critical frontend functions
- [ ] **[FEAT]** Add rate limiting to auth endpoints (prevent brute force)
- [ ] **[FEAT]** Add input sanitization middleware

---

## Completed

- [x] FastAPI backend with JWT auth
- [x] MongoDB Motor async integration
- [x] Farmer profile CRUD API
- [x] 7-stage OCR pipeline (Tesseract + OpenCV + PyMuPDF)
- [x] Multi-strategy Tesseract auto-detection (`ocr/config.py`)
- [x] YAML rules engine for scheme eligibility
- [x] ML-based scheme success probability (scheme_success_model.pkl)
- [x] Knowledge graph MWIS bundling (NetworkX)
- [x] Benefit predictor (per-hectare + flat-rate)
- [x] Crop recommender ML model (crop_model.pkl)
- [x] Predictive alert service (heuristic)
- [x] Community stories API (CRUD + upvote toggle)
- [x] React 19 SPA with Vite
- [x] TailwindCSS + Shadcn/UI component library
- [x] Profile Wizard (3-step with OCR auto-fill)
- [x] Dashboard with scheme recommendations
- [x] Community Hub with story creation
- [x] Multi-language support (en, hi, mr, gu) via i18next
- [x] Voice input (Web Speech API) for profile fields
- [x] Dark mode support (next-themes)
- [x] Landing page with 3D animations (Three.js, GSAP, tsParticles)
- [x] ProtectedRoute with profile completeness check
- [x] Policy ingestor (regex-based PDF constraint extraction)
- [x] Monitoring endpoints (OCR health, scheme monitor)
