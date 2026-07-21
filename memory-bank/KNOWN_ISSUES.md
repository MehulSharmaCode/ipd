# KNOWN_ISSUES.md — Current Bugs, Debt & Limitations
> **Last Updated:** 2026-07-21 | Update this file whenever a bug is found or fixed.

---

## 🔴 Critical Issues

### KI-001: Hardcoded Secret Key in .env
**Severity:** Critical (Security)
**File:** `backend/.env`
**Description:** `SECRET_KEY=my_super_secret_hackathon_key_123` — predictable, committed to version control pattern
**Impact:** Any actor with access to the repo can forge JWT tokens
**Fix:** Generate a strong random key: `python -c "import secrets; print(secrets.token_hex(32))"`
**Status:** ⚠️ Unresolved

### KI-002: No Unique DB Index on `farmers.email`
**Severity:** Critical (Data Integrity)
**File:** `backend/app/api/auth.py`
**Description:** Email uniqueness is enforced by `find_one()` at signup, not at the MongoDB level. Race condition possible under concurrent signup.
**Impact:** Duplicate email accounts possible under high concurrency
**Fix:** Add MongoDB unique index: `db.farmers.create_index("email", unique=True)`
**Status:** ⚠️ Unresolved

### KI-003: JWT in localStorage (XSS Vulnerability)
**Severity:** Critical (Security)
**File:** `frontend/src/lib/api.ts`, `frontend/src/pages/AuthPage.tsx`
**Description:** JWT stored in `localStorage` is accessible to any JavaScript (XSS attacks)
**Impact:** Stolen tokens if XSS vulnerability exists anywhere in the app
**Fix:** Use HttpOnly + SameSite=Strict cookies with refresh token rotation
**Status:** ⚠️ Known trade-off, deferred for hackathon

---

## 🟡 High Priority Issues

### KI-004: Recommendations Recomputed on Every Request
**Severity:** High (Performance)
**Files:** `backend/app/api/farmers.py`, `backend/app/ml/services/recommendation_service.py`
**Description:** Every `GET /api/farmers/me` triggers full ML pipeline (rules filter + ML inference + graph computation)
**Impact:** High latency (~500ms-2s per request), cannot scale to many users
**Fix:** Cache recommendations in MongoDB or Redis; invalidate on profile update
**Status:** ⚠️ Unresolved

### KI-005: Debug Print Statements in Production Code
**Severity:** High (Code Quality / Security)
**Files:** `backend/app/core/security.py`, `backend/app/api/auth.py`, `backend/app/api/farmers.py`
**Description:** `🕵️ DEBUG: get_current_user received token: eyJ...` prints sensitive token fragments to server logs
**Impact:** Token fragments exposed in server logs; performance overhead
**Fix:** Remove all `print()` debug statements; replace with `logger.debug()` behind DEBUG flag
**Status:** ⚠️ Unresolved

### KI-006: Hardcoded API Base URL in Frontend
**Severity:** High (Deployment)
**File:** `frontend/src/lib/api.ts`
**Description:** `baseURL: "http://127.0.0.1:8000/api"` — hardcoded localhost URL
**Impact:** Cannot deploy frontend to production without code changes
**Fix:** Use Vite env variable: `baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api"`
**Status:** ⚠️ Unresolved

### KI-007: Hardcoded CORS Origins in main.py
**Severity:** High (Deployment)
**File:** `backend/app/main.py`
**Description:** CORS origins are hardcoded to localhost:5173-5175
**Impact:** Frontend cannot connect if deployed to different origin
**Fix:** Load CORS origins from `.env`
**Status:** ⚠️ Unresolved

### KI-008: Age Calculation Uses Hardcoded 2025
**Severity:** High (Logic Bug)
**File:** `backend/app/ml/ocr/mapping.py:_parse_year_to_age()`
**Description:** `age = 2025 - year` — will be wrong in 2026+
**Fix:** `from datetime import datetime; age = datetime.now().year - year`
**Status:** ⚠️ Unresolved (NOW WRONG — current year is 2026)

---

## 🟠 Medium Priority Issues

### KI-009: No Docker Configuration
**Severity:** Medium (Deployment)
**Description:** No `Dockerfile`, `docker-compose.yml`, or deployment scripts
**Impact:** Complex manual setup; not reproducible across environments
**Fix:** Add Docker Compose with MongoDB + backend + frontend services
**Status:** ❌ Not implemented

### KI-010: Legacy OCR Engine Files
**Severity:** Medium (Code Quality)
**Files:** `backend/app/ml/ocr/ocr_engine.py`, `backend/app/ml/ocr/ocr_engine_v2.py`
**Description:** Legacy OCR engines with Windows-hardcoded Tesseract paths (`C:\Program Files\Tesseract-OCR\tesseract.exe`)
**Impact:** Confusing codebase; if imported before `config.py`, they override the correct path
**Fix:** Delete `ocr_engine.py` and `ocr_engine_v2.py`; ensure all code imports from `ocr_service.py`
**Status:** ⚠️ Partially mitigated (ocr_service.py re-applies correct path on every call)

### KI-011: No Password Reset Flow
**Severity:** Medium (UX)
**Description:** Users who forget their password have no way to reset it
**Fix:** Implement email-based password reset with time-limited tokens
**Status:** ❌ Not implemented

### KI-012: No Token Revocation / Logout
**Severity:** Medium (Security)
**Description:** JWT tokens cannot be invalidated server-side; "logout" only removes token from localStorage
**Impact:** If token is stolen, it remains valid for 24h
**Fix:** Implement token blacklist (Redis) or reduce token lifetime + refresh tokens
**Status:** ⚠️ Known limitation

### KI-013: Story Upvote Count Can Go Negative
**Severity:** Medium (Logic Bug)
**File:** `backend/app/api/stories.py:upvote_story()`
**Description:** When removing upvote: `story.get("upvotes", 1) - 1` — if upvotes was 0, returns -1
**Fix:** Use MongoDB atomic `$inc: {upvotes: -1}` only if current upvotes > 0; or accept the -1 and use `max(0, upvotes)` on frontend
**Status:** ⚠️ Unresolved

### KI-014: No Story Edit or Delete Endpoints
**Severity:** Medium (UX)
**File:** `backend/app/api/stories.py`
**Description:** No `PUT /api/stories/{id}` or `DELETE /api/stories/{id}` endpoints
**Impact:** Farmers cannot correct or remove their stories
**Status:** ❌ Not implemented

### KI-015: `ocr_engine.py` Imports at Wrong Level
**Severity:** Medium (Code Risk)
**Files:** `backend/app/ml/ocr/ocr_engine.py`, `ocr_engine_v2.py`
**Description:** These files set pytesseract.tesseract_cmd to a Windows path at module import time. If Python imports them before `config.py`, it overrides the correct OS detection.
**Mitigation:** `ocr_service.py` re-applies the correct path on every call
**Fix:** Delete legacy files

---

## 🟢 Low Priority Issues

### KI-016: Scheme Rules Only Cover 10 Schemes
**Severity:** Low (Scope)
**File:** `backend/app/ml/rules/schemes_rules.yaml`
**Description:** Only 10 government schemes are modeled; dozens more exist
**Fix:** Add more schemes to YAML
**Status:** ⚠️ Partial implementation

### KI-017: Predictive Alerts Are Purely Heuristic
**Severity:** Low (Accuracy)
**File:** `backend/app/services/predictive_alert_service.py`
**Description:** Alerts are static rules; no real weather data
**Fix:** Integrate OpenWeatherMap or IMD API
**Status:** ❌ Not implemented

### KI-018: Community Stories Moderation Missing
**Severity:** Low (UX)
**Description:** No admin moderation, reporting, or content filtering
**Status:** ❌ Not implemented

### KI-019: `is_verified` Check for Story Posting is Commented Out
**Severity:** Low (Business Logic)
**File:** `backend/app/api/stories.py:create_story()`
**Description:** The check `if not is_verified: raise 403` is commented out
**Impact:** Unverified farmers can post stories (was intended to be gated)
**Status:** ⚠️ Intentional for testing; restore for production

### KI-020: `LOKY_MAX_CPU_COUNT` Hardcoded to 4
**Severity:** Low (Portability)
**File:** `backend/app/main.py`
**Description:** `os.environ["LOKY_MAX_CPU_COUNT"] = "4"` assumes a 4-core machine
**Fix:** Remove or use `os.cpu_count()`

### KI-021: No Pagination for Farmers List
**Severity:** Low (Performance)
**File:** `backend/app/api/farmers.py:get_all_farmers()`
**Description:** `GET /api/farmers/` fetches all farmers with no limit
**Fix:** Add `skip` and `limit` query parameters

### KI-022: Dump Directory Contains Outdated Code
**Severity:** Low (Cleanup)
**Directory:** `dump/`
**Description:** Contains older versions of backend, frontend, ML code
**Impact:** Confusion for new developers
**Fix:** Either clean up or document what it contains

### KI-023: DOB Year Range Cap at 2024
**Severity:** Low (Logic)
**File:** `backend/app/ml/ocr/validation.py:validate_dob()`
**Description:** `if not (1900 <= year <= 2024)` — rejects years 2025-2026
**Fix:** Use `datetime.now().year` dynamically
**Status:** ⚠️ Unresolved (linked to KI-008)

### KI-024: TSParticles / Three.js Performance on Low-End Devices
**Severity:** Low (UX)
**File:** `frontend/src/pages/LandingPage.tsx`
**Description:** 3D animations + particle effects may cause performance issues on older/mobile devices
**Fix:** Add `prefers-reduced-motion` media query support; lazy-load 3D components

---

## Technical Debt Summary

| Area | Debt Level |
|---|---|
| Security (JWT in localStorage, no token revocation) | 🔴 Critical |
| Secret key management | 🔴 Critical |
| Debug logging cleanup | 🟡 High |
| Docker / deployment | 🟡 High |
| Environment variable management | 🟡 High |
| Database indexes | 🟡 High |
| Performance (recomputed recommendations) | 🟡 High |
| Age/DOB hardcoded year | 🟡 High |
| Legacy OCR files cleanup | 🟠 Medium |
| Missing CRUD endpoints (story edit/delete) | 🟠 Medium |
| Scheme coverage (only 10 schemes) | 🟢 Low |
| Static alert heuristics | 🟢 Low |
