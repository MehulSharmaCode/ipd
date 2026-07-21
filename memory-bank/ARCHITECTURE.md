# ARCHITECTURE.md — AgriSense System Architecture
> **Last Updated:** 2026-07-21 | Cross-reference: PROJECT_CONTEXT.md, API_REFERENCE.md

---

## Overview

AgriSense is a full-stack web application with:
- **Frontend**: React 19 SPA (Vite) — TypeScript, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI (Python) — async REST API
- **Database**: MongoDB (Motor async driver)
- **ML Engine**: Embedded in backend (`app/ml/`) — Tesseract OCR, Scikit-learn, NetworkX, PyTorch
- **Auth**: JWT (HS256, 24h expiry, bcrypt password hashing)

---

## Frontend Architecture

### Entry Point
```
frontend/src/main.jsx
  └─ renders <App /> into #root
```

### App Shell (`App.tsx`)
Wraps entire app in:
1. `ThemeProvider` (next-themes, dark default, localStorage key: `agrisense-theme`)
2. `BrowserRouter` (React Router v7)
3. Global `<Toaster />` (Sonner)
4. `<Navbar />` (always visible)

### Routes
| Path | Component | Guard |
|---|---|---|
| `/` | `LandingPage` | Public |
| `/auth` | `AuthPage` | Public |
| `/community` | `CommunityHub` | Public |
| `/profile-setup` | `ProfileWizard` | `ProtectedRoute(requireProfile=false)` |
| `/dashboard` | `Dashboard` | `ProtectedRoute(requireProfile=true)` |
| `*` | `Navigate to "/"` | — |

### ProtectedRoute Logic
```
ProtectedRoute
  1. Check localStorage.access_token
  2. If token exists → GET /api/farmers/me
  3. Determine profile completeness:
     - profile_wizard_complete === true OR
     - (is_aadhar_verified && is_pan_verified)  ← legacy fallback
  4a. Not authenticated → redirect to /auth
  4b. On /profile-setup AND profile complete → redirect to /dashboard
  4c. requireProfile=true AND not complete → redirect to /profile-setup
  4d. Otherwise → render children
```

### API Client (`lib/api.ts`)
```typescript
axios.create({ baseURL: 'http://127.0.0.1:8000/api' })

Request interceptor:
  → attaches Authorization: Bearer <token from localStorage>

Response interceptor:
  → logs errors globally
```

### Pages

#### LandingPage.tsx (~36KB)
- Hero section with 3D / particle animations (Three.js, tsParticles, GSAP)
- Features showcase
- Community stories preview (calls GET /api/stories/top)
- CTA buttons (→ /auth)

#### AuthPage.tsx (~7KB)
- Tab toggle: Login / Signup
- Login: POST /api/auth/login (OAuth2 form: username=email, password)
- Signup: POST /api/auth/signup (full_name, email, password)
- On success: stores access_token, redirects to /profile-setup

#### ProfileWizard.tsx (~30KB)
- 3-step wizard:
  - Step 1: Basic info (name, age, gender, category, state, district, pincode, annual_income, bank_account)
  - Step 2: Agricultural data (land_size, farmer_type, soil_type, irrigation_type, water_source, land_ownership, crop_season, primary_crops)
  - Step 3: Document upload (Aadhaar + PAN cards via file input → POST /api/upload/)
- Voice input available for numeric fields (useVoiceInput hook)
- OCR auto-fill: profileSuggestions from API populate form fields
- On Step 3 complete: PUT /api/farmers/me with profile_wizard_complete=true

#### Dashboard.tsx (~80KB, largest file)
- Scheme recommendations display (ranked_schemes, recommended_bundles)
- Ineligible schemes with explanations
- Predictive alerts section
- Crop recommendation widget (POST /api/farmers/recommend-crop)
- Scheme monitor (GET /api/monitoring/schemes/latest)
- Profile summary

#### CommunityHub.tsx (~15KB)
- Stories list with crop/state/scheme filters
- Top stories carousel
- Create story modal (CreateStoryModal.tsx)
- Upvote interaction

### Components

#### Navbar.tsx
- Language switcher (LanguageSwitcher)
- Dark/light mode toggle
- Auth links (Login/Signup or Dashboard/Logout)

#### CreateStoryModal.tsx
- Dialog (Shadcn) for submitting a success story
- Fields: title, content, crop_type, location_state, scheme_id, tags

#### DarkVeil.tsx
- Background WebGL effect using OGL

#### CropShowcase.tsx
- Visual crop display with metadata

### Hooks
| Hook | Purpose |
|---|---|
| `useVoiceInput` | Web Speech API — supports en-IN, hi-IN, mr-IN, gu-IN; strips non-digits for numeric fields |
| `useTranslationText` | Convenience wrapper around i18next `t()` |

### i18n
```
i18n/
  i18n.ts       → i18next setup (lazy backend loading, language detection)
  locales/
    en.json     → English (base)
    hi.json     → Hindi
    mr.json     → Marathi
    gu.json     → Gujarati
```
Language detection: browser preference → localStorage fallback.

### UI Components (Shadcn/UI)
Badge, Button, Card, Dialog, Input, Label, Progress, Select, Separator, Sonner (Toaster), Tabs

---

## Backend Architecture

### Entry Point (`app/main.py`)
```python
FastAPI(title="AgriSense API", version="1.0.0", lifespan=lifespan)

Lifespan:
  startup  → connect_to_mongo()
  shutdown → close_mongo_connection()

CORS origins: localhost:5173, 5174, 5175

Routers:
  /api/auth      → auth.router
  /api/farmers   → farmers.router
  /api/upload    → upload.router
  /api/stories   → stories.router
  /api/monitoring → monitoring_router
  (prefix-less)  → documents_router
```

### Core Modules (`app/core/`)

#### config.py
```python
class Settings:
    MONGO_URI = env("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME = env("DATABASE_NAME", "agrisense_db")
    SECRET_KEY = env("SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
```

#### database.py
```python
# Singleton pattern
db_instance = Database()
# Async Motor client
db_instance.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db_instance.db = client[DATABASE_NAME]

# Public API:
get_db()              → returns db_instance.db
get_collection(name)  → returns db_instance.db[name]
```

#### security.py
```python
# Password
verify_password(plain, hashed)  → bcrypt.checkpw
get_password_hash(password)     → bcrypt.hashpw(gensalt())

# JWT
create_access_token(data, expires_delta)  → jwt.encode({"sub": user_id, "exp": ...})

# Dependency injection
get_current_user(token=Depends(oauth2_scheme))
  → decode JWT
  → fetch farmer by ObjectId from "farmers" collection
  → return farmer dict (with _id as string)
```

### API Modules (`app/api/`)

#### auth.py
- `POST /signup`: check unique email, hash password, insert minimal farmer, return FarmerResponse
- `POST /login`: find by email (normalized lowercase), verify bcrypt, return JWT Token

#### farmers.py
- `GET /me`: auth-required, fetch farmer, trigger recommendations + alerts, return FarmerResponse
- `PUT /me`: auth-required, update only sent fields (exclude_unset=True), re-trigger recommendations
- `POST /`: legacy internal create (no auth)
- `GET /{farmer_id}`: fetch by ObjectId
- `GET /`: list all (no recommendations for performance)
- `POST /recommend-crop`: auth-required, maps soil_type + crop_season to NPK/weather features, calls CropRecommender

#### upload.py
- `POST /`: auth-required, validate (MIME + 10MB size), save to `uploads/`, run OCR pipeline, update farmer DB, return OCR results
- Accepted types: PDF, JPEG, PNG, WebP
- Filename format: `{user_id}_{doc_type}_{uuid8}.{ext}`

#### stories.py
- `POST /`: auth-required, create StoryDB with farmer_id + farmer_name
- `GET /`: public, filterable (crop, state, scheme_id), paginated (skip/limit)
- `GET /top`: public, top 3 by upvotes (for landing page)
- `GET /{story_id}`: public, fetch by ObjectId
- `POST /{story_id}/upvote`: auth-required, toggle (add/remove)

#### monitoring.py
- `GET /ocr-health`: returns OCR config summary (tesseract path, version, availability)
- `GET /system-status`: triggers SchemeMonitor.scrape_latest_schemes()
- `POST /refresh-schemes`: background task — scrape + log
- `POST /test/policy-ingest`: sync PDF → text → PolicyIngestor.extract_rules()
- `GET /schemes/latest`: same as system-status but designed for dashboard polling
- `POST /policy/ingest`: background task — ingest raw policy text

---

## Database Architecture

### Connection
Motor async client → `agrisense_db`

### Collections

#### `farmers`
Primary entity. See DATABASE.md for full schema.
Key fields: email (unique), hashed_password, profile_wizard_complete, recommended_schemes (computed), aadhar_number, pan_number, primary_crops

#### `stories`
Community stories. Key fields: farmer_id (ref), upvotes (int), upvoted_by (list of farmer_ids)

No formal relationships or foreign keys — MongoDB document model. References are string IDs.

---

## Authentication Architecture

```
Client                          Server
  │                               │
  │ POST /api/auth/login           │
  │ (username=email, password)    │
  │ ──────────────────────────►  │
  │                               ├─ find farmer by email
  │                               ├─ bcrypt.checkpw(password, hash)
  │                               ├─ jwt.encode({sub: farmer._id, exp: now+1440min})
  │ ◄────────────────────────── │
  │ {access_token, token_type}   │
  │                               │
  │ GET /api/farmers/me           │
  │ Authorization: Bearer <token> │
  │ ──────────────────────────►  │
  │                               ├─ oauth2_scheme extracts token
  │                               ├─ jwt.decode(token, SECRET_KEY)
  │                               ├─ db.farmers.find_one({_id: ObjectId(sub)})
  │                               ├─ return farmer dict
  │ ◄────────────────────────── │
  │ FarmerResponse + schemes     │
```

---

## ML Engine Architecture

See OCR_PIPELINE.md and FEATURES.md for detailed pipeline docs.

### Module Map

```
app/ml/
├── ocr/                         # OCR subsystem
│   ├── config.py                # Tesseract auto-detection (multi-strategy)
│   ├── preprocessing.py         # cv2 image pipeline (deskew, threshold, denoise)
│   ├── ocr_service.py           # Tesseract execution + result container
│   ├── classification.py        # Rule-based document type classification
│   ├── parsers.py               # AadhaarParser, PANParser (regex)
│   ├── validation.py            # Field validators (aadhaar 12-digit, PAN format)
│   ├── mapping.py               # OCR fields → FarmerProfile suggestions
│   ├── pipeline.py              # Orchestrator (7-stage entry point)
│   ├── ocr_engine.py            # Legacy (Windows path hardcoded, being replaced)
│   ├── ocr_engine_v2.py         # Legacy v2
│   └── ocr_service.py           # Current active service
│
├── rules/
│   ├── rules_engine.py          # YAML-based eligibility filter
│   └── schemes_rules.yaml       # 10 scheme definitions with rules + benefit_calculation
│
├── inference/
│   ├── ranking_engine.py        # Main orchestrator: SchemeRankingEngine.rank_schemes()
│   ├── success_predictor.py     # .pkl model inference: predict_success()
│   ├── benefit_predictor.py     # Financial value calculation (flat-rate/per-hectare)
│   ├── crop_recommender.py      # crop_model.pkl → recommend_crop()
│   └── document_classifier.py  # document_classifier.pt → classify document
│
├── models/
│   ├── registry.py              # ModelRegistry.load_model(name) → joblib.load
│   ├── scheme_success_model.pkl # ~1MB trained model
│   ├── crop_model.pkl           # ~44MB trained model (LightGBM)
│   └── document_classifier.pt  # ~0.5MB PyTorch model
│
├── graph/
│   └── knowledge_graph.py       # SchemeKnowledgeGraph — MWIS via NetworkX complement+cliques
│
├── features/
│   ├── feature_store.py         # FeatureStore.build_features() — normalize farmer profile
│   └── feature_definitions.py  # Feature metadata
│
├── services/
│   └── recommendation_service.py  # Singleton SchemeRankingEngine wrapper
│
├── reinforcement/
│   ├── policy_engine.py         # SchemePolicy.select_scheme() — RL epsilon-greedy
│   └── interaction_logger.py   # log_interaction() — records feedback
│
├── explainability/
│   └── scheme_explainer.py      # SchemeExplainer.explain_eligible/ineligible()
│
├── policy_engine/
│   └── policy_ingestor.py       # PolicyIngestor.extract_rules() — regex constraint extraction
│
├── preprocessing/
│   ├── data_cleaning.py         # Profile data cleaning
│   ├── encoders.py              # Feature encoding
│   └── feature_engineering.py  # Feature engineering
│
└── utils/
    ├── logger.py                # get_logger() — standard logging
    └── profile_mapper.py        # map_farmer_to_ml_features() — farmer dict → ML feature vector
```

### Recommendation Pipeline Data Flow

```
farmer_profile (dict from MongoDB)
  │
  ▼ FeatureStore.build_features()
normalized_features
  │
  ▼ RulesEngine.filter_schemes(features)
  ├── eligible_schemes   → [scheme objects with passed_rules]
  └── ineligible_schemes → [scheme objects with failed_rules]
        │
        ▼ map_farmer_to_ml_features(features)
        base_ml_features (DataFrame-compatible dict)
          │
          ▼ for each eligible_scheme:
            ml_features = base_ml_features + {"scheme": scheme_id}
            probability = SchemeSuccessPredictor.predict_success(ml_features)
            benefit = BenefitPredictor.predict_benefit(scheme, ml_features)
            scheme["financial_benefit"] = benefit.predicted_financial_value
          │
          ▼ sort by probability (desc)
          ranked_results
            │
            ▼ KnowledgeGraph.get_optimal_scheme_bundles(ranked_results)
            → subgraph of eligible scheme nodes
            → complement graph
            → nx.find_cliques() → valid_bundles (independent sets)
            → sort bundles by total_benefit_value
            recommended_bundles
              │
              ▼ SchemePolicy.select_scheme(scheme_ids)
              selected_scheme (RL epsilon-greedy)
```

---

## Data Flow Diagrams

### User Registration → Dashboard
```
Register ──► Login ──► JWT ──► Profile Wizard ──► OCR Upload ──► Dashboard
  MongoDB      bcrypt    localStorage   PUT /me      Tesseract     GET /me
  insert        verify    store         update       pipeline      + ML engine
```

### OCR Upload Flow
```
File Input
  → POST /api/upload/ (multipart)
  → validate(MIME, size)
  → save to uploads/
  → preprocess (OpenCV: upscale, deskew, bilateral filter, adaptive threshold)
  → extract_text (Tesseract: --oem 3 --psm 6)
  → classify (keyword matching → AADHAAR_FRONT/AADHAAR_BACK/PAN/UNKNOWN)
  → parse (AadhaarParser or PANParser regex)
  → validate (12-digit Aadhaar, PAN format, DOB range)
  → map (OCR fields → profile field suggestions)
  → update DB (if valid: set aadhaar/pan_number + verified flag)
  → return JSON { documentType, confidence, fields, validation, profileSuggestions }
```

---

## Module Dependencies

```
main.py
  └── api/auth.py, farmers.py, upload.py, stories.py, monitoring.py
        ├── core/config.py, database.py, security.py
        ├── models/farmer.py, story.py
        ├── services/predictive_alert_service.py, scheme_monitor.py
        └── ml/
              ├── ocr/pipeline.py
              │     ├── ocr/ocr_service.py → ocr/config.py, ocr/preprocessing.py
              │     ├── ocr/classification.py
              │     ├── ocr/parsers.py
              │     ├── ocr/validation.py
              │     └── ocr/mapping.py
              ├── services/recommendation_service.py
              │     └── inference/ranking_engine.py
              │           ├── rules/rules_engine.py → rules/schemes_rules.yaml
              │           ├── inference/success_predictor.py → models/registry.py → .pkl
              │           ├── inference/benefit_predictor.py
              │           ├── graph/knowledge_graph.py
              │           ├── features/feature_store.py
              │           ├── reinforcement/policy_engine.py
              │           ├── explainability/scheme_explainer.py
              │           └── utils/profile_mapper.py, logger.py
              └── inference/crop_recommender.py → models/registry.py → crop_model.pkl
```
