# FEATURES.md — AgriSense Feature Documentation
> **Last Updated:** 2026-07-21 | Cross-reference: API_REFERENCE.md, ARCHITECTURE.md

---

## Feature 1: User Authentication

**Purpose:** Secure account creation and login with JWT session management.

### Files Involved
- `backend/app/api/auth.py` — Route handlers
- `backend/app/core/security.py` — JWT + bcrypt utilities
- `backend/app/models/farmer.py` — FarmerSignup, Token models
- `frontend/src/pages/AuthPage.tsx` — Login/Signup UI
- `frontend/src/lib/api.ts` — Axios with JWT interceptor
- `frontend/src/components/ProtectedRoute.tsx` — Route guard

### Backend APIs
- `POST /api/auth/signup` — Create account (name, email, password)
- `POST /api/auth/login` — Get JWT token (OAuth2 form)

### Frontend Components
- `AuthPage.tsx` — Tab-based Login/Signup form
- `ProtectedRoute.tsx` — Checks token + profile completeness

### Flow
1. User submits signup form → `POST /api/auth/signup`
2. Server validates unique email, hashes password (bcrypt), inserts minimal farmer record
3. User logs in → `POST /api/auth/login` → JWT (24h) returned
4. Frontend stores token in `localStorage.access_token`
5. All subsequent requests: Axios interceptor attaches `Authorization: Bearer <token>`
6. `ProtectedRoute` calls `GET /api/farmers/me` to validate token and check `profile_wizard_complete`

### Dependencies
- bcrypt (password hashing)
- PyJWT + python-jose (JWT)
- Pydantic EmailStr (email validation)

### Limitations
- Tokens are not revocable (no blacklist)
- No refresh token mechanism
- No password reset flow
- No email verification
- Secret key is hardcoded in `.env` (should be rotated in production)

---

## Feature 2: Farmer Profile Wizard

**Purpose:** Guided 3-step onboarding flow that collects agricultural and identity data.

### Files Involved
- `backend/app/api/farmers.py` — PUT /me endpoint
- `backend/app/models/farmer.py` — FarmerProfile schema
- `frontend/src/pages/ProfileWizard.tsx` — 3-step wizard UI
- `frontend/src/hooks/useVoiceInput.ts` — Voice field input

### Backend APIs
- `PUT /api/farmers/me` — Update profile (any subset of fields)
- `GET /api/farmers/me` — Fetch current profile

### Frontend Components
- `ProfileWizard.tsx` — 3 steps:
  - Step 1: Basic info (name, age, gender, category, state, district, pincode, income, bank account)
  - Step 2: Agricultural data (land size, farmer type, soil type, irrigation, water source, land ownership, season, crops)
  - Step 3: Document upload (Aadhaar + PAN via OCR)

### Key Logic
- Each step calls `PUT /api/farmers/me` with only that step's fields
- Step 3 triggers OCR via `POST /api/upload/` and auto-fills fields from `profileSuggestions`
- On completion of Step 3: sends `profile_wizard_complete: true`
- `ProtectedRoute` then allows access to `/dashboard`

### Limitations
- No step persistence if browser refreshes mid-wizard (state is in-memory)
- No back-navigation that saves data
- OCR auto-fill requires user confirmation (suggestions only)

---

## Feature 3: AI Scheme Recommendations

**Purpose:** Rank government welfare schemes for a specific farmer using rules + ML.

### Files Involved
- `backend/app/api/farmers.py` — triggers recommendations
- `backend/app/ml/services/recommendation_service.py` — service layer
- `backend/app/ml/inference/ranking_engine.py` — main orchestrator
- `backend/app/ml/rules/rules_engine.py` — YAML eligibility filter
- `backend/app/ml/rules/schemes_rules.yaml` — 10 scheme definitions
- `backend/app/ml/inference/success_predictor.py` — .pkl ML model
- `backend/app/ml/inference/benefit_predictor.py` — financial value calc
- `backend/app/ml/graph/knowledge_graph.py` — MWIS bundling
- `backend/app/ml/models/scheme_success_model.pkl` — trained model (~1MB)
- `backend/app/ml/features/feature_store.py` — feature normalization
- `backend/app/ml/utils/profile_mapper.py` — farmer dict → ML features
- `backend/app/ml/reinforcement/policy_engine.py` — RL selection
- `backend/app/ml/explainability/scheme_explainer.py` — human-readable explanations
- `frontend/src/pages/Dashboard.tsx` — schemes display

### Backend APIs
- `GET /api/farmers/me` — returns `recommended_schemes`, `recommended_bundles`, `ineligible_schemes`

### Scheme Rules (schemes_rules.yaml)
10 schemes defined:
| Scheme ID | Name | Benefit |
|---|---|---|
| PM_KISAN | PM Kisan Samman Nidhi | ₹6,000 flat |
| DRIP_IRRIGATION | Drip Irrigation Subsidy | ₹40,000/ha |
| CROP_INSURANCE | Pradhan Mantri Fasal Bima Yojana | ₹15,000/ha |
| SMALL_FARMER_SUPPORT | Small Farmer Development Scheme | ₹5,000 flat |
| MEDIUM_FARMER_MODERNIZATION | Medium Farmer Modernization | ₹80,000/ha |
| LARGE_FARMER_IRRIGATION_SUPPORT | Large Farmer Irrigation Support | ₹1,00,000/ha |
| COTTON_SUPPORT_SCHEME | Cotton Farmer Support | ₹25,000 flat |
| RICE_DEVELOPMENT_SCHEME | Rice Development Subsidy | ₹12,000/ha |
| SUGARCANE_INCENTIVE | Sugarcane Farmer Incentive | ₹20,000/ha |
| LOW_INCOME_FARMER_AID | Low Income Farmer Aid Program | ₹10,000 flat |

### ML Models
- `scheme_success_model.pkl` — predicts approval probability (0–1) for farmer×scheme
- Features: land_size, income, farmer_type, crop, irrigation, scheme_id, etc.

### Knowledge Graph
- NetworkX graph of scheme nodes with conflict edges
- MWIS solved via complement graph + `nx.find_cliques()`
- Bundles ranked by total financial value

### Reinforcement Learning
- `SchemePolicy` uses epsilon-greedy selection
- `log_interaction()` records farmer-scheme interactions for future training

### Response Format
```json
{
  "recommended_schemes": [
    {
      "scheme_id": "PM_KISAN",
      "scheme_name": "PM Kisan Samman Nidhi",
      "success_probability": 0.87,
      "explanation": ["Farmer type matches: small", "Income ≤ ₹2,00,000"],
      "predicted_financial_value": 6000,
      "benefit_type": "Direct Financial Transfer",
      "prediction_explanation": "Flat rate direct benefit transfer."
    }
  ],
  "recommended_bundles": [
    {
      "bundle_id": "BUNDLE_01",
      "total_benefit_value": 46000,
      "total_benefit": "₹46,000",
      "schemes": [...],
      "graph_explanation": "These schemes form an optimal bundle..."
    }
  ],
  "ineligible_schemes": [
    {
      "scheme_id": "LARGE_FARMER_IRRIGATION_SUPPORT",
      "explanation": ["farmer_type must be 'large' (got 'small')"]
    }
  ]
}
```

### Limitations
- Recommendations recomputed on every `GET /api/farmers/me` (expensive for large user counts)
- Only 10 schemes in the YAML (should be expanded)
- ML model accuracy depends on training data quality
- RL feedback loop not connected to real outcomes

---

## Feature 4: OCR Document Processing

**Purpose:** Extract identity data from Aadhaar/PAN cards to auto-fill profile fields.

### Files Involved
- `backend/app/api/upload.py` — upload endpoint
- `backend/app/ml/ocr/` — 17 files (see OCR_PIPELINE.md)

### APIs
- `POST /api/upload/` — multipart: file + doc_type

### Supported Documents
- Aadhaar card (front + back)
- PAN card

### What It Extracts
| Document | Fields |
|---|---|
| Aadhaar Front | name, aadhaarNumber (12 digits), dob, birthYear, gender |
| Aadhaar Back | name, aadhaarNumber (if visible), address keywords |
| PAN | name, fatherName, panNumber, dob |

### Auto-fill Suggestions Returned
| Document | Profile Fields Suggested |
|---|---|
| Aadhaar | full_name_ocr_suggestion, aadhar_number, gender, age, dob |
| PAN | full_name_ocr_suggestion, pan_number, dob |

See `OCR_PIPELINE.md` for complete details.

---

## Feature 5: Predictive Alerts

**Purpose:** Generate weather and crop risk alerts based on farmer's location and crop data.

### Files Involved
- `backend/app/services/predictive_alert_service.py` — alert generation
- `backend/app/models/farmer.py` — PredictiveAlert model

### APIs
Included in response of: `GET /api/farmers/me` and `PUT /api/farmers/me`

### Alert Types
```python
PredictiveAlert:
  alert_type: str     # "weather_risk", "crop_risk", "general_risk"
  severity: str       # "low", "medium", "high", "critical"
  message: str
  timestamp: str      # ISO 8601 UTC
  recommended_action: str | None
```

### Current Heuristics
| State | Crop | Risk | Severity |
|---|---|---|---|
| Maharashtra | Sugarcane | Water Scarcity | high |
| Maharashtra | Cotton | Bollworm Pest Alert | medium |
| Maharashtra | Onion | Unseasonal Rain | critical |
| Punjab | Wheat | High Temperature | high |
| Punjab | Rice | Groundwater Depletion | medium |
| Any | Kharif season | Monsoon irregularities | medium |
| Any | Rabi season | Cold wave | low |

### Limitations
- No real weather API integration
- Static heuristics based on state + crop combination
- Only 2 states (Maharashtra, Punjab) have crop-specific data
- Alerts do not update based on actual weather conditions

### Future Plan
- Integrate OpenWeatherMap API for real-time data
- Add more states and crop combinations
- Implement time-based alert scheduling

---

## Feature 6: Community Stories

**Purpose:** Allow farmers to share success stories about government schemes.

### Files Involved
- `backend/app/api/stories.py` — CRUD + upvote
- `backend/app/models/story.py` — StoryDB, StoryResponse
- `frontend/src/pages/CommunityHub.tsx` — stories display
- `frontend/src/components/CreateStoryModal.tsx` — creation form

### APIs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /api/stories/ | Required | Create story |
| GET | /api/stories/ | None | List (filterable) |
| GET | /api/stories/top | None | Top 3 by upvotes |
| GET | /api/stories/{id} | None | Get single |
| POST | /api/stories/{id}/upvote | Required | Toggle upvote |

### Story Fields
- `title` (required), `content` (required)
- Optional: `crop_type`, `location_state`, `location_district`, `scheme_id`, `media_url`, `tags[]`
- Auto-set: `farmer_id`, `farmer_name`, `upvotes=0`, `upvoted_by=[]`, `created_at`, `updated_at`

### Filtering (GET /api/stories/)
- `crop` — regex, case-insensitive match on `crop_type`
- `state` — regex match on `location_state`
- `scheme_id` — exact match
- `limit` — max 100 (default 20)
- `skip` — pagination offset

### Limitations
- No moderation system (any farmer can post anything)
- `is_verified` check is commented out (all farmers can post regardless of verification)
- No edit (PUT) or delete (DELETE) endpoints for stories
- `media_url` field exists but frontend doesn't support media uploads yet

---

## Feature 7: Crop Recommendation

**Purpose:** Recommend the best crop for a farmer's soil type and season using ML.

### Files Involved
- `backend/app/api/farmers.py:recommend_crop()` — endpoint
- `backend/app/ml/inference/crop_recommender.py` — ML inference
- `backend/app/ml/models/crop_model.pkl` — trained model (~44MB)

### API
- `POST /api/farmers/recommend-crop` (auth required)

### Input → Feature Mapping
```python
soil_type → NPK values + ph:
  Alluvial: N=40, P=40, K=40, ph=7.0
  Black:    N=30, P=50, K=60, ph=7.5
  Red:      N=20, P=30, K=30, ph=6.0
  Laterite: N=15, P=25, K=25, ph=5.5
  Desert:   N=10, P=20, K=20, ph=8.0
  Mountain: N=45, P=40, K=35, ph=6.5

crop_season → weather:
  Kharif: temp=30.0, humidity=75.0, rainfall=250.0
  Rabi:   temp=20.0, humidity=55.0, rainfall=50.0
  Zaid:   temp=35.0, humidity=40.0, rainfall=20.0
```

### Response
```json
{ "recommended_crop": "Rice", "status": "success" }
```

### Limitations
- NPK and weather values are synthetic mappings (not real sensor data)
- Loaded lazily (first request) — cold start latency possible

---

## Feature 8: Multi-language Support

**Purpose:** UI available in English, Hindi, Marathi, and Gujarati.

### Files Involved
- `frontend/src/i18n/i18n.ts` — i18next configuration
- `frontend/src/i18n/locales/en.json` — English (~20KB)
- `frontend/src/i18n/locales/hi.json` — Hindi (~36KB)
- `frontend/src/i18n/locales/mr.json` — Marathi (~29KB)
- `frontend/src/i18n/locales/gu.json` — Gujarati (~28KB)
- `frontend/src/components/LanguageSwitcher.tsx` — UI toggle
- `frontend/src/hooks/useTranslationText.ts` — translation hook

### Language Detection Priority
1. Browser language preference
2. `localStorage.agrisense-language`
3. Falls back to English

### Voice Input Languages (useVoiceInput.ts)
Supported BCP47 tags: `en-IN`, `hi-IN`, `mr-IN`, `gu-IN`

---

## Feature 9: Scheme Monitoring

**Purpose:** Monitor government portals for new/updated schemes.

### Files Involved
- `backend/app/services/scheme_monitor.py` — web scraper
- `backend/app/api/monitoring.py` — endpoints

### Current Behavior
- Attempts to scrape `https://agricoop.nic.in/en/Agriculture`
- If scraping fails → returns hardcoded mock data:
  - PMKSY guidelines updated
  - National Mission on Natural Farming

### APIs
- `GET /api/monitoring/system-status` — trigger + return
- `GET /api/monitoring/schemes/latest` — for dashboard polling
- `POST /api/monitoring/refresh-schemes` — async background trigger

### Limitations
- Mock data only (scraping rarely succeeds due to anti-bot measures)
- No database persistence for scraped data
- No scheduled background refresh

---

## Feature 10: Policy Intelligence Engine

**Purpose:** Extract eligibility rules from policy PDF documents.

### Files Involved
- `backend/app/ml/policy_engine/policy_ingestor.py` — regex extraction
- `backend/app/ml/ocr/document_parser.py` — PDF text extraction
- `backend/app/api/monitoring.py` — endpoints

### Extracted Constraints
- `min_land_hectares` — "minimum X hectares"
- `max_land_hectares` — "maximum X hectares"
- `min_age` / `max_age` — "age above X" or "between X and Y"
- `required_crops` — keyword matching (wheat, rice, cotton, sugarcane, maize, soybean, onion)

### APIs
- `POST /api/monitoring/test/policy-ingest` — sync PDF upload + extraction (for demo)
- `POST /api/monitoring/policy/ingest` — async background text ingestion

### Limitations
- Regex-based (not LLM-based) — misses complex/ambiguous language
- Does not save to DB (returns inline only)
- `test/policy-ingest` endpoint is demonstration-only
