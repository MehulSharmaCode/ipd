# PROJECT_CONTEXT.md — AgriSense
> **Last Updated:** 2026-07-21 | **Maintained by:** AI Software Engineer (Antigravity)
> **Rule:** Read this file FIRST in every new session. Verify against codebase before acting.

---

## Project Purpose

**AgriSense** (repo: `binary-brains`) is an **Intelligent Scheme Discovery Platform for Indian Farmers**. Its mission is to bridge the gap between rural farmers and government agricultural welfare schemes — making it easy to discover eligibility, auto-fill documents via OCR, and receive AI-ranked recommendations.

Built as an **Intra-Project Development (IPD) / hackathon project** by team Binary Brains.

---

## Problem Statement

Millions of Indian farmers are unable to access government welfare schemes (PM Kisan, PMFBY, Drip Irrigation subsidies, etc.) because:
- Schemes are fragmented across central and state portals
- Eligibility criteria are complex, written in bureaucratic language
- Farmers lack digital literacy or access to English-language information
- Document upload and verification is manual and cumbersome

AgriSense solves this by:
1. **AI-powered eligibility matching** — rules engine + ML model ranks schemes for a farmer's profile
2. **OCR-assisted document upload** — scan Aadhaar/PAN; system auto-fills profile fields
3. **Multi-language support** — UI in English, Hindi, Marathi, Gujarati (+ voice input)
4. **Community stories** — farmers share scheme success stories
5. **Predictive alerts** — weather and crop risk warnings

---

## Current Completion Status (2026-07-21)

| Module | Status | Notes |
|---|---|---|
| Backend API (FastAPI) | ✅ Complete | Fully operational |
| Authentication (JWT) | ✅ Complete | bcrypt + HS256 JWT, 24h expiry |
| Farmer Profile CRUD | ✅ Complete | Auth-gated PUT/GET |
| OCR Pipeline (Aadhaar + PAN) | ✅ Complete | Tesseract-based, 7-stage pipeline |
| Scheme Recommendation (Rules + ML) | ✅ Complete | YAML rules + .pkl model |
| Knowledge Graph Bundling (MWIS) | ✅ Complete | NetworkX |
| Predictive Alert Service | ⚠️ Heuristic | Static rules, no live API |
| Scheme Monitor | ⚠️ Mock fallback | Attempts scraping, falls back to mock |
| Policy Ingestor | ⚠️ Regex-based | Not LLM-based yet |
| Community Stories API | ✅ Complete | CRUD + upvote toggle |
| Frontend — Landing Page | ✅ Complete | 3D + particles + GSAP |
| Frontend — Auth Page | ✅ Complete | Login + Signup |
| Frontend — Profile Wizard | ✅ Complete | 3-step with OCR |
| Frontend — Dashboard | ✅ Complete | Schemes + alerts + bundles |
| Frontend — Community Hub | ✅ Complete | Stories + crop showcase |
| Multi-language (en/hi/mr/gu) | ✅ Complete | i18next + 4 locale files |
| Voice Input | ✅ Complete | Web Speech API |
| Crop Recommender (ML) | ✅ Complete | crop_model.pkl |
| Docker / Deployment | ❌ Missing | Not configured |
| Real Weather API | ❌ Missing | Pending integration |
| Real Scheme Scraping | ❌ Missing | Pending |

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Primary language |
| FastAPI | ≥0.112.0 | REST API framework |
| Uvicorn | ≥0.30.0 | ASGI server |
| Pydantic | ≥2.8.0 | Data validation & serialization |
| Motor | 3.3.2 | Async MongoDB driver |
| PyMongo | 4.6.2 | MongoDB utilities |
| LightGBM | latest | Underlying ML library |
| Scikit-learn | latest | ML pipeline + model loading |
| Pandas / NumPy | latest | Data manipulation |
| Pytesseract | latest | Tesseract OCR wrapper |
| OpenCV (cv2) | latest | Image preprocessing |
| PyMuPDF (fitz) | latest | PDF-to-image conversion |
| PyTorch | latest | Document classifier (.pt) |
| PyJWT / python-jose | latest | JWT encoding/decoding |
| bcrypt | latest | Password hashing |
| PyYAML | latest | Scheme rules YAML |
| NetworkX | latest | Knowledge graph (MWIS) |
| BeautifulSoup4 | 4.12.3 | Web scraping |
| Requests | 2.32.3 | HTTP client |
| Joblib | latest | ML model serialization |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 19.2.0 | UI framework |
| TypeScript | — | Type safety |
| Vite | ≥7.3 | Build tool / dev server |
| TailwindCSS | 3.4.x | CSS framework |
| React Router | v7.13 | Client-side routing |
| Axios | 1.13.x | HTTP client with JWT interceptors |
| Framer Motion | 12.x | Page/component animations |
| Three.js + R3F | 0.183.x / 9.x | 3D hero animations |
| GSAP | 3.14.x | Advanced scroll/timeline animations |
| tsParticles | 3.x | Particle background effects |
| i18next + react-i18next | 25.x / 16.x | Internationalization |
| Shadcn/UI (Radix UI) | latest | Accessible UI component library |
| Lucide React | 0.577.x | Icon set |
| Sonner | 2.x | Toast notifications |
| next-themes | 0.4.x | Dark mode support |
| Geist (font) | — | Typography |

### Database
| Detail | Value |
|---|---|
| Engine | MongoDB |
| Local connection | mongodb://127.0.0.1:27017 |
| Database name | agrisense_db |
| Collections | farmers, stories |
| Driver | Motor (async) |

---

## Folder Overview

```
binary-brains/
├── backend/
│   ├── app/
│   │   ├── main.py              # Entry point: CORS, lifespan, router registration
│   │   ├── api/                 # HTTP route handlers (6 files)
│   │   │   ├── auth.py          # POST /signup, POST /login
│   │   │   ├── farmers.py       # GET/PUT /me, GET /{id}, GET /, POST /recommend-crop
│   │   │   ├── upload.py        # POST / (file upload + OCR)
│   │   │   ├── stories.py       # CRUD + upvote
│   │   │   ├── monitoring.py    # OCR health, scheme monitor, policy ingest
│   │   │   └── documents.py     # ML document endpoints (legacy/internal)
│   │   ├── core/
│   │   │   ├── config.py        # Settings class (reads .env)
│   │   │   ├── database.py      # Motor MongoDB connection
│   │   │   └── security.py      # JWT utils, password hash, get_current_user
│   │   ├── models/
│   │   │   ├── farmer.py        # FarmerProfile, FarmerResponse, Token, alerts, schemes
│   │   │   ├── story.py         # StoryDB, StoryResponse
│   │   │   └── scheme.py        # Scheme data models
│   │   ├── services/
│   │   │   ├── predictive_alert_service.py  # Heuristic weather/crop alerts
│   │   │   └── scheme_monitor.py            # Web scraper for scheme updates
│   │   └── ml/
│   │       ├── ocr/             # Full OCR pipeline (17 files)
│   │       ├── inference/       # ML inference (ranking, success predictor, etc.)
│   │       ├── rules/           # YAML rules engine + schemes_rules.yaml
│   │       ├── models/          # .pkl + .pt model files + registry.py
│   │       ├── graph/           # Knowledge graph MWIS (NetworkX)
│   │       ├── policy_engine/   # Policy PDF constraint extractor
│   │       ├── reinforcement/   # RL interaction logger + policy
│   │       ├── explainability/  # Scheme explanation generator
│   │       ├── features/        # Feature store + definitions
│   │       ├── preprocessing/   # Data cleaning + encoders
│   │       ├── datasets/        # Training data utilities
│   │       ├── services/        # recommendation_service.py
│   │       └── utils/           # Logger, profile_mapper
│   ├── scripts/verify_ocr.py    # OCR health check script
│   ├── uploads/                 # Runtime file storage
│   ├── .env                     # Secrets (not committed)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router + ThemeProvider + Navbar
│   │   ├── main.jsx             # React entry point
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx  # Hero + features + community preview
│   │   │   ├── AuthPage.tsx     # Login / Signup tabs
│   │   │   ├── ProfileWizard.tsx # 3-step profile + OCR upload
│   │   │   ├── Dashboard.tsx    # Scheme recommendations + alerts
│   │   │   └── CommunityHub.tsx # Stories + crop showcase
│   │   ├── components/
│   │   │   ├── ProtectedRoute.tsx    # Auth + profile completion guard
│   │   │   ├── Navbar.tsx            # Top navigation
│   │   │   ├── CreateStoryModal.tsx  # Story creation modal
│   │   │   ├── CropShowcase.tsx      # Crop visualization
│   │   │   ├── DarkVeil.tsx          # Background veil effect
│   │   │   ├── LanguageSwitcher.tsx  # Language toggle
│   │   │   ├── theme-provider.tsx    # next-themes wrapper
│   │   │   └── ui/                   # 11 Shadcn primitives
│   │   ├── hooks/
│   │   │   ├── useVoiceInput.ts      # Web Speech API (en/hi/mr/gu)
│   │   │   └── useTranslationText.ts # i18n helper
│   │   ├── lib/
│   │   │   ├── api.ts                # Axios instance with JWT interceptors
│   │   │   └── utils.ts              # cn() Tailwind utility
│   │   └── i18n/
│   │       ├── i18n.ts               # i18next configuration
│   │       └── locales/              # en.json, hi.json, mr.json, gu.json
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── tsconfig.json
│
├── dump/                        # Archived/legacy code
├── memory-bank/                 # THIS FOLDER — AI Memory Bank
└── test.png                     # Test image for OCR debugging
```

---

## High-Level Architecture Diagram

```
[Browser :5173]
    │ JWT in localStorage
    │ Axios with Bearer token interceptor
    ▼
[React SPA (Vite + React Router)]
    │ axios.create({ baseURL: 'http://127.0.0.1:8000/api' })
    ▼
[FastAPI :8000]
    ├── CORS: localhost:5173-5175
    ├── /api/auth/*         → Signup, Login
    ├── /api/farmers/*      → Profile CRUD + Recommendations + Crop Recommend
    ├── /api/upload/*       → Document upload + OCR trigger
    ├── /api/stories/*      → Community stories CRUD + upvote
    └── /api/monitoring/*   → OCR health, scheme monitor, policy ingest
          │
          ├── [MongoDB :27017 → agrisense_db]
          │     ├── farmers (collection)
          │     └── stories (collection)
          │
          └── [ML Engine]
                ├── OCR Pipeline (Tesseract + OpenCV + PyMuPDF)
                ├── Rules Engine (schemes_rules.yaml, 10 schemes)
                ├── SchemeSuccessPredictor (scheme_success_model.pkl ~1MB)
                ├── CropRecommender (crop_model.pkl ~44MB)
                ├── DocumentClassifier (document_classifier.pt ~0.5MB)
                ├── BenefitPredictor (rule-based, per-hectare or flat-rate)
                ├── KnowledgeGraph (NetworkX MWIS algorithm)
                └── PredictiveAlertService (heuristic rules by state+crop)
```

---

## Key Workflows

### 1. Registration & Login
`POST /api/auth/signup` → create minimal farmer record (name, email, hashed_password) → `POST /api/auth/login` (OAuth2PasswordRequestForm) → JWT → `localStorage.access_token`

### 2. Profile Wizard
`ProtectedRoute (requireProfile=false)` → `/profile-setup`:
- Step 1: Basic info (name, age, gender, state, district, pincode, income)
- Step 2: Agricultural data (land_size, farmer_type, soil_type, irrigation, crops, season)
- Step 3: Document upload (Aadhaar/PAN via OCR) + profile_wizard_complete=true
→ `PUT /api/farmers/me` → redirect to `/dashboard`

### 3. OCR Pipeline (7 Stages)
`POST /api/upload/` → validate mime+size → save to `uploads/` →
1. File validation
2. OCR (Tesseract via pytesseract)
3. Classification (AADHAAR_FRONT/AADHAAR_BACK/PAN)
4. Field parsing (AadhaarParser/PANParser regex)
5. Validation (aadhaar 12-digit, PAN format, DOB range)
6. Profile mapping (OCR fields → FarmerProfile suggestions)
7. Response + DB update (if valid)
→ return profileSuggestions to frontend for auto-fill

### 4. Scheme Recommendation
`GET /api/farmers/me` → `RecommendationService.get_recommendations()` → `SchemeRankingEngine.rank_schemes()`:
1. `FeatureStore.build_features(farmer_profile)` — normalize + clean
2. `RulesEngine.filter_schemes(features)` — YAML hard eligibility gate
3. `SchemeSuccessPredictor.predict_success(ml_features)` — .pkl probability
4. `BenefitPredictor.predict_benefit(scheme, features)` — financial value
5. `KnowledgeGraph.get_optimal_scheme_bundles(eligible)` — MWIS bundles
6. `SchemePolicy.select_scheme(scheme_ids)` — RL best scheme
→ ranked_schemes + recommended_bundles + ineligible_schemes

### 5. Community Stories
- Public: `GET /api/stories/` (filterable by crop/state/scheme_id), `GET /api/stories/top`
- Auth: `POST /api/stories/` (create), `POST /api/stories/{id}/upvote` (toggle)

---

## Business Logic Summary

- **YAML rules are hard gates** — a scheme only reaches ML scoring if ALL rules pass
- **ML adds probabilistic ranking** — `scheme_success_model.pkl` scores each farmer×scheme pair
- **Knowledge Graph prevents conflicts** — schemes with `conflicts_with` edges cannot co-exist in a bundle
- **OCR is best-effort** — upload always returns success; extracted data is suggestions only
- **JWT is 24h (1440 min)** — stored in localStorage, attached via Axios request interceptor
- **`profile_wizard_complete`** is the primary ProtectedRoute gate for dashboard access
- **Tesseract detection** is multi-strategy: env var → PATH → known platform defaults (macOS/Linux/Windows)
- **Benefit calculation** is dynamic: flat-rate or per_hectare_subsidy × land_size × crop_multiplier

---

## Development Roadmap

**Critical**
- Docker Compose setup (MongoDB + backend + frontend)
- Move API base URL to `.env` / Vite env variable

**High**
- Real weather API integration (OpenWeatherMap)
- Real scheme scraping (government portals)
- Scheme application history per farmer

**Medium**
- Admin dashboard for scheme management
- LLM-based policy PDF parsing (replace regex PolicyIngestor)
- Push notifications for scheme deadlines/weather alerts

**Low**
- Mobile app (React Native or Flutter)
- More Indian languages (Tamil, Telugu, Kannada)
- Government API integration for application status tracking
