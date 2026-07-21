# CHANGELOG.md — AgriSense Development History
> **Last Updated:** 2026-07-21 | Format: [Version] — Date | Author

---

## [Sprint 1 — Session 1] — 2026-07-21 | Lead Software Engineer (AI)

### Fixed — Backend
- **[C-01]** `mapping.py` — Age calculation was hardcoded to `2025`. Now uses `datetime.now().year`. Affected every Aadhaar card OCR age field.
- **[C-02]** `validation.py` — DOB year cap was hardcoded to `2024`. Now uses `datetime.now().year`. Affected DOB validation for any year > 2024.
- **[A-05/J-02]** `auth.py` — Removed all 5 `print()` debug statements that leaked email addresses and login status to server logs. Replaced with structured `logger` calls.
- **[A-05/J-02]** `security.py` — Removed all 6 `print()` debug statements that exposed JWT token fragments and decoded payloads to server logs. Replaced with structured `logger` calls.
- **[A-05]** `farmers.py` — Removed 5 `print()` debug statements from recommendation and alert handlers. Replaced with `logger` calls.
- **[G-02]** `farmers.py` — Added null check on `updated_farmer` after `find_one()` in `PUT /api/farmers/me`. Previously crashed with `NoneType` AttributeError if DB returned no document.
- **[G-05]** `farmers.py` — Replaced bare `except:` patterns with `except Exception as e:` in recommendation error handlers.

### Fixed — Frontend
- **[A-06]** `api.ts` — Removed `console.log` from Axios request interceptor that logged token activity on every API call.
- **[A-06]** `AuthPage.tsx` — Removed 4 `console.log` statements that logged user email addresses on login and signup attempts.
- **[A-06]** `Dashboard.tsx` — Removed `console.log` that logged extracted policy rules to browser console.
- **[E-01]** `Dashboard.tsx` — Added `toast.success()` feedback on logout. Previously silent with no user confirmation.

### Created — Documentation
- **[NEW]** `memory-bank/FEATURE_MATRIX.md` — Full feature inventory with status across all 14 features.

---

## [Initial Build] — 2026-07-21 | Team Binary Brains

### Added — Backend
- FastAPI application with lifespan management (startup: MongoDB connect, shutdown: disconnect)
- CORS configuration for localhost:5173-5175
- JWT authentication (HS256, 24h expiry, bcrypt password hashing)
- `POST /api/auth/signup` — farmer account creation
- `POST /api/auth/login` — OAuth2 token endpoint
- `GET/PUT /api/farmers/me` — authenticated profile management
- `GET/POST /api/farmers/` — farmer listing and legacy creation
- `GET /api/farmers/{id}` — farmer lookup by ObjectId
- `POST /api/farmers/recommend-crop` — ML-powered crop recommendation
- `POST /api/upload/` — multipart document upload with OCR pipeline
- `POST /api/stories/` — community story creation
- `GET /api/stories/` — filterable story listing (crop, state, scheme_id)
- `GET /api/stories/top` — top 3 stories by upvotes (landing page)
- `GET /api/stories/{id}` — single story lookup
- `POST /api/stories/{id}/upvote` — toggle upvote
- `GET /api/monitoring/ocr-health` — Tesseract diagnostic
- `GET /api/monitoring/system-status` — scheme monitor
- `POST /api/monitoring/refresh-schemes` — background scraping trigger
- `POST /api/monitoring/test/policy-ingest` — sync PDF constraint extraction
- `POST /api/monitoring/policy/ingest` — async policy text ingestion
- MongoDB Motor async client with singleton pattern
- Pydantic v2 models: FarmerProfile, FarmerResponse, StoryDB, StoryResponse, Token

### Added — OCR Pipeline
- `ocr/config.py` — 4-strategy Tesseract auto-detection (env → PATH → platform defaults → error)
- `ocr/preprocessing.py` — 7-step image preprocessing (upscale, grayscale, deskew, bilateral filter, adaptive threshold, morphological opening, border pad)
- `ocr/ocr_service.py` — Tesseract execution wrapper with timing and confidence extraction
- `ocr/classification.py` — Rule-based document type classification (AADHAAR_FRONT/BACK/PAN)
- `ocr/parsers.py` — AadhaarParser + PANParser with regex field extraction
- `ocr/validation.py` — Field validators (12-digit Aadhaar, PAN format, DOB range)
- `ocr/mapping.py` — OCR fields → FarmerProfile suggestions mapper
- `ocr/pipeline.py` — 7-stage orchestrator (the ONLY OCR entry point)
- `scripts/verify_ocr.py` — OCR diagnostic/health check script

### Added — ML Engine
- `ml/rules/rules_engine.py` — YAML-based eligibility hard-gate filter
- `ml/rules/schemes_rules.yaml` — 10 government scheme definitions with rules + benefit_calculation
- `ml/features/feature_store.py` — Farmer profile normalization and feature building
- `ml/inference/ranking_engine.py` — SchemeRankingEngine main orchestrator
- `ml/inference/success_predictor.py` — SchemeSuccessPredictor (.pkl ML inference)
- `ml/inference/benefit_predictor.py` — BenefitPredictor (flat-rate + per-hectare)
- `ml/inference/crop_recommender.py` — CropRecommender (.pkl ML inference)
- `ml/inference/document_classifier.py` — DocumentClassifier (.pt PyTorch)
- `ml/graph/knowledge_graph.py` — SchemeKnowledgeGraph MWIS via NetworkX
- `ml/services/recommendation_service.py` — Singleton SchemeRankingEngine wrapper
- `ml/reinforcement/policy_engine.py` — SchemePolicy epsilon-greedy RL
- `ml/reinforcement/interaction_logger.py` — Interaction logging for RL
- `ml/explainability/scheme_explainer.py` — Human-readable scheme explanations
- `ml/policy_engine/policy_ingestor.py` — Regex-based PDF constraint extractor
- `ml/models/registry.py` — ModelRegistry (joblib model loading)
- `ml/models/scheme_success_model.pkl` — Trained scheme success model (~1MB)
- `ml/models/crop_model.pkl` — Trained crop recommendation model (~44MB)
- `ml/models/document_classifier.pt` — PyTorch document classifier (~0.5MB)
- `ml/utils/profile_mapper.py` — Farmer dict → ML feature vector
- `ml/utils/logger.py` — Standard logging utility

### Added — Services
- `services/predictive_alert_service.py` — Heuristic weather/crop alerts by state+crop
- `services/scheme_monitor.py` — Web scraper with mock fallback

### Added — Frontend
- React 19 + Vite 7 + TypeScript SPA
- TailwindCSS 3.4 + Shadcn/UI component library
- React Router v7 with 5 routes
- `App.tsx` — ThemeProvider + Router + Toaster shell
- `LandingPage.tsx` — Hero + 3D animations (Three.js, R3F, GSAP, tsParticles, OGL) + features showcase + community preview
- `AuthPage.tsx` — Tab-based Login/Signup forms
- `ProfileWizard.tsx` — 3-step wizard with voice input + OCR auto-fill
- `Dashboard.tsx` — Scheme recommendations + bundles + alerts + crop recommender
- `CommunityHub.tsx` — Stories feed + top stories + filters
- `ProtectedRoute.tsx` — JWT validation + profile completeness guard
- `Navbar.tsx` — Navigation + language switcher + dark mode toggle
- `CreateStoryModal.tsx` — Story creation dialog
- `DarkVeil.tsx` — Background WebGL effect (OGL)
- `CropShowcase.tsx` — Crop visualization component
- `LanguageSwitcher.tsx` — Language selection UI
- `useVoiceInput.ts` — Web Speech API hook (en-IN, hi-IN, mr-IN, gu-IN)
- `useTranslationText.ts` — i18next helper hook
- `lib/api.ts` — Axios instance with JWT request interceptor + error response interceptor
- `lib/utils.ts` — cn() TailwindCSS class merge utility
- `i18n/i18n.ts` — i18next configuration with browser language detection
- `i18n/locales/en.json` — English translations (~20KB)
- `i18n/locales/hi.json` — Hindi translations (~36KB)
- `i18n/locales/mr.json` — Marathi translations (~29KB)
- `i18n/locales/gu.json` — Gujarati translations (~28KB)
- Shadcn/UI primitives: Badge, Button, Card, Dialog, Input, Label, Progress, Select, Separator, Sonner, Tabs

---

## Upcoming Changes (not yet implemented)

See `TODO.md` for full task list.

**Key pending items:**
- Docker Compose setup
- Environment variable configuration
- Real weather API integration
- Password reset flow
- Story edit/delete
- MongoDB performance indexes
- Test coverage
