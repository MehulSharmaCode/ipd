# API_REFERENCE.md — AgriSense REST API
> **Last Updated:** 2026-07-21 | **Base URL:** http://127.0.0.1:8000/api
> Cross-reference: ARCHITECTURE.md, DATABASE.md

---

## Authentication

All protected endpoints require:
```
Authorization: Bearer <JWT access_token>
```
Token is obtained from `POST /api/auth/login` and stored in `localStorage.access_token`.

JWT payload: `{ "sub": "<farmer_mongo_id>", "exp": <unix_timestamp> }`

---

## Auth Endpoints (`/api/auth`)

### POST /api/auth/signup
Create a new farmer account.

**Auth:** None (public)

**Request Body (JSON):**
```json
{
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "password": "SecurePassword123!"
}
```

**Response 201:**
```json
{
  "_id": "68769abc...",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "primary_crops": [],
  "documents_uploaded": [],
  "is_differently_abled": false,
  "bank_account_linked": false,
  "profile_wizard_complete": false,
  "is_aadhar_verified": false,
  "is_pan_verified": false,
  "recommended_schemes": [],
  "ineligible_schemes": [],
  "predictive_alerts": []
}
```

**Errors:**
- `400 Email already registered` — duplicate email

**Implementation:** `backend/app/api/auth.py:signup()`

---

### POST /api/auth/login
Login and obtain a JWT token.

**Auth:** None (public)

**Request Body (OAuth2PasswordRequestForm — form-encoded, NOT JSON):**
```
username=ramesh@example.com&password=SecurePassword123!
```
> Note: `username` field holds the email. This is the OAuth2 standard.

**Response 200:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Incorrect email or password` — user not found or wrong password

**Implementation:** `backend/app/api/auth.py:login()`

---

## Farmer Endpoints (`/api/farmers`)

### GET /api/farmers/me
Fetch the currently authenticated farmer's profile including AI-generated recommendations.

**Auth:** Required

**Response 200 (FarmerResponse):**
```json
{
  "_id": "68769abc...",
  "full_name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "phone_number": "+919876543210",
  "age": 35,
  "gender": "Male",
  "state": "Maharashtra",
  "land_size_hectares": 2.5,
  "primary_crops": ["Rice", "Wheat"],
  "profile_wizard_complete": true,
  "is_aadhar_verified": true,
  "is_pan_verified": false,
  "recommended_schemes": [
    {
      "scheme_id": "PM_KISAN",
      "scheme_name": "PM Kisan Samman Nidhi",
      "success_probability": 0.87,
      "explanation": ["Farmer type matches: small", "Land size ≤ 2 ha"],
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
      "scheme_name": "Large Farmer Irrigation Support",
      "explanation": ["farmer_type must be 'large' (got 'small')"]
    }
  ],
  "predictive_alerts": [
    {
      "alert_type": "weather_risk",
      "severity": "medium",
      "message": "Monsoon irregularities detected...",
      "timestamp": "2026-07-21T17:00:00",
      "recommended_action": "Ensure drainage systems are clear."
    }
  ]
}
```

**Errors:**
- `401` — invalid or missing token

**Implementation:** `backend/app/api/farmers.py:get_my_profile()`
**Side effects:** Triggers `RecommendationService` and `PredictiveAlertService` on every call.

---

### PUT /api/farmers/me
Update the current farmer's profile. Only sent fields are updated (`exclude_unset=True`).

**Auth:** Required

**Request Body (JSON — any subset of FarmerProfile fields):**
```json
{
  "age": 40,
  "land_size_hectares": 3.5,
  "primary_crops": ["Cotton", "Soybean"],
  "soil_type": "Black",
  "crop_season": "Kharif",
  "profile_wizard_complete": true
}
```

**Response 200:** Same as GET /farmers/me (with fresh recommendations).

**Notes:**
- `email` and `hashed_password` are stripped even if sent (security)
- Triggers fresh recommendations and alerts

**Implementation:** `backend/app/api/farmers.py:update_my_profile()`

---

### POST /api/farmers/recommend-crop
Get an AI crop recommendation based on soil type and crop season.

**Auth:** Required

**Request Body (JSON):**
```json
{
  "soil_type": "Black",
  "crop_season": "Kharif"
}
```

**Soil types:** Alluvial, Black, Red, Laterite, Desert, Mountain
**Seasons:** Kharif, Rabi, Zaid

**Response 200:**
```json
{
  "recommended_crop": "Rice",
  "status": "success"
}
```

**Errors:**
- `503 Crop recommendation model is not available` — if model failed to load
- `500 Crop recommendation failed: <reason>` — inference error

**Implementation:** `backend/app/api/farmers.py:recommend_crop()`
**ML Model:** `app/ml/models/crop_model.pkl` (~44MB)

---

### GET /api/farmers/{farmer_id}
Get a farmer's profile by MongoDB ObjectId.

**Auth:** None (public)

**Response 200:** FarmerResponse (with recommendations)
**Errors:**
- `400 Invalid Farmer ID`
- `404 Farmer not found`

---

### GET /api/farmers/
Get all farmers (without recommendations — performance optimization).

**Auth:** None (public)
**Response 200:** `List[FarmerResponse]`

---

### POST /api/farmers/
Create a farmer (legacy/internal, no auth required).

**Request Body:** FarmerProfile JSON
**Response 201:** FarmerResponse with recommendations

---

## Upload Endpoints (`/api/upload`)

### POST /api/upload/
Upload a government document (Aadhaar or PAN) for OCR processing.

**Auth:** Required

**Request Body (multipart/form-data):**
```
file: <binary file>
doc_type: "aadhar" | "pan"
```

**Constraints:**
- Max file size: 10MB
- Accepted MIME types: `application/pdf`, `image/jpeg`, `image/png`, `image/jpg`, `image/webp`

**Response 200:**
```json
{
  "status": "success",
  "filename": "68769abc_aadhar_a1b2c3d4.jpg",
  "documentType": "AADHAAR_FRONT",
  "confidence": 78.4,
  "fields": {
    "aadhaarNumber": "1234 5678 9012",
    "name": "Ramesh Kumar",
    "dob": "15/08/1988",
    "birthYear": "1988",
    "gender": "Male"
  },
  "validation": {
    "valid": true,
    "warnings": []
  },
  "profileSuggestions": {
    "full_name_ocr_suggestion": "Ramesh Kumar",
    "aadhar_number": "1234 5678 9012",
    "gender": "Male",
    "age": 37,
    "dob": "15/08/1988"
  },
  "processingTimeMs": 1243.7
}
```

**On validation failure:**
```json
{
  "status": "success",
  "documentType": "AADHAAR_FRONT",
  "confidence": 45.2,
  "fields": { "name": "Ramesh Kumar" },
  "validation": {
    "valid": false,
    "warnings": ["Aadhaar number could not be extracted."]
  },
  "profileSuggestions": {},
  "processingTimeMs": 987.3
}
```

**Errors:**
- `400 Invalid file type` — unsupported MIME
- `413 File size exceeds the 10 MB limit`
- `500 Could not save file`

**Side effects:** If validation passes, updates farmer DB record with aadhaar/pan_number and sets `is_aadhar_verified` or `is_pan_verified` to true.

**Implementation:** `backend/app/api/upload.py:upload_document()`
**Pipeline:** `app/ml/ocr/pipeline.py:process()`

---

## Stories Endpoints (`/api/stories`)

### POST /api/stories/
Create a new community success story.

**Auth:** Required

**Request Body (JSON):**
```json
{
  "title": "How PM Kisan Changed My Life",
  "content": "I received ₹6000 directly in my bank account...",
  "crop_type": "Rice",
  "location_state": "Punjab",
  "location_district": "Ludhiana",
  "scheme_id": "PM_KISAN",
  "tags": ["success", "pmkisan"]
}
```

**Response 201:**
```json
{
  "_id": "68769abc...",
  "title": "...",
  "farmer_id": "68769abc...",
  "farmer_name": "Ramesh Kumar",
  "upvotes": 0,
  "upvoted_by": [],
  "created_at": "2026-07-21T17:00:00",
  ...
}
```

---

### GET /api/stories/
List community stories with optional filters.

**Auth:** None (public)

**Query Params:**
| Param | Type | Default | Description |
|---|---|---|---|
| crop | string | null | Filter by crop_type (regex, case-insensitive) |
| state | string | null | Filter by location_state (regex) |
| scheme_id | string | null | Filter by scheme_id (exact) |
| limit | int | 20 | Max items (1-100) |
| skip | int | 0 | Pagination offset |

**Response 200:** `List[StoryResponse]` sorted by created_at DESC

---

### GET /api/stories/top
Get top 3 stories by upvote count (used on landing page).

**Auth:** None
**Response 200:** `List[StoryResponse]` (max 3, sorted by upvotes DESC)

---

### GET /api/stories/{story_id}
Get a single story by MongoDB ObjectId.

**Auth:** None
**Errors:** `400 Invalid story ID format`, `404 Story not found`

---

### POST /api/stories/{story_id}/upvote
Toggle upvote on a story (add if not upvoted, remove if already upvoted).

**Auth:** Required

**Response 200:**
```json
{ "detail": "Upvote added", "upvotes": 5 }
```
or:
```json
{ "detail": "Upvote removed", "upvotes": 4 }
```

---

## Monitoring Endpoints (`/api/monitoring`)

### GET /api/monitoring/ocr-health
Check Tesseract OCR engine availability.

**Auth:** None
**Response 200:**
```json
{
  "status": "ok",
  "tesseract_cmd": "/opt/homebrew/bin/tesseract",
  "tesseract_available": true,
  "version": "tesseract 5.5.2",
  "tessdata_prefix": "/opt/homebrew/share/tessdata",
  "detection_method": "Discovered via which/PATH",
  "platform": "Darwin",
  "machine": "arm64"
}
```

---

### GET /api/monitoring/system-status
Get latest scheme monitoring data (scraping result or mock fallback).

**Auth:** None
**Response 200:**
```json
{
  "status": "ok",
  "recent_updates": [
    {
      "id": "SCH-PMKSY-2026",
      "title": "Pradhan Mantri Krishi Sinchayee Yojana Guidelines Updated",
      "url": "https://pmksy.gov.in/",
      "source": "Ministry of Agriculture",
      "status": "Updated",
      "description": "...",
      "insights": ["Focus on micro-irrigation", ...]
    }
  ]
}
```

---

### GET /api/monitoring/schemes/latest
Same as system-status but designed for dashboard polling (no `status` wrapper).

---

### POST /api/monitoring/refresh-schemes
Trigger a background scheme scraping task.

**Auth:** None
**Response 200:** `{ "message": "Scheme refresh initiated in the background." }`

---

### POST /api/monitoring/test/policy-ingest
Upload a PDF and synchronously extract policy constraints using the regex engine.

**Auth:** None
**Request Body (multipart/form-data):** `file: <PDF>`
**Response 200:**
```json
{
  "message": "Successfully ingested SchemeName",
  "extracted_rules": {
    "min_land_hectares": 1.5,
    "max_land_hectares": null,
    "min_age": 18,
    "max_age": 60,
    "required_crops": ["Wheat", "Rice"]
  },
  "raw_text_snippet": "..."
}
```

---

### POST /api/monitoring/policy/ingest
Ingest raw policy document text in the background.

**Auth:** None
**Query Params:** `scheme_name: str`, `document_text: str`
**Response 200:** `{ "message": "Policy ingestion for '...' started in the background." }`

---

## Root Endpoint

### GET /
Health check.
**Response 200:** `{ "message": "Welcome to the AgriSense API. System is operational." }`

---

## Error Format

FastAPI standard error format:
```json
{
  "detail": "Error message here"
}
```

## Common HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation, duplicate) |
| 401 | Unauthorized (missing/invalid JWT) |
| 403 | Forbidden |
| 404 | Not Found |
| 413 | Payload Too Large (file upload) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (ML model not loaded) |
