# FEATURE MATRIX — Binary Brains / Kisan Sahayak

> Last Updated: 2026-07-21
> Sprint: Sprint 1 (Stability)
> Status Legend: ✅ Working | ⚠️ Partial | ❌ Broken | 🔲 Untested | 🚧 In Progress

---

## 1. Authentication

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Allow farmers to register, log in, and maintain secure sessions |
| **Backend** | ✅ FastAPI `/api/auth/signup` and `/api/auth/login` (OAuth2 + JWT) |
| **Frontend** | ⚠️ `AuthPage.tsx` works but uses `window.location.href` instead of `navigate()` |
| **API** | ✅ `POST /api/auth/signup`, `POST /api/auth/login` |
| **Database** | ✅ MongoDB `farmers` collection stores `email` + `hashed_password` |
| **UI** | ✅ Toggle between Login/Register forms |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ✅ Core flow works |
| **Known Issues** | Debug prints removed (C-01 ✅). No AuthContext. `window.location.href` causes full reload (A-02 pending). No token refresh. |
| **Overall** | ⚠️ Functional but fragile |

---

## 2. Session Persistence / Protected Routes

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Ensure only authenticated users access Dashboard and Profile Wizard |
| **Backend** | ✅ `get_current_user` dependency in `security.py` validates JWT on every protected route |
| **Frontend** | ⚠️ `ProtectedRoute.tsx` reads `localStorage` directly. No `AuthContext`. Navbar auth state doesn't sync same-tab. |
| **API** | ✅ 401 returned when token is invalid/expired |
| **Database** | ✅ User looked up on every request |
| **UI** | ⚠️ Navbar auth button lags without full reload |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Works on page load; breaks on same-tab login/logout |
| **Known Issues** | A-01, A-02, A-03 — AuthContext needed. Sprint 1. |
| **Overall** | ⚠️ Partial |

---

## 3. Profile Wizard (Onboarding)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Multi-step form to collect farmer profile data |
| **Backend** | ✅ `PUT /api/farmers/me` persists profile data |
| **Frontend** | ⚠️ 3-step wizard in `ProfileWizard.tsx`. No back button on step 1. `wizard_complete` flag set prematurely. |
| **API** | ✅ `PUT /api/farmers/me` |
| **Database** | ✅ Updates `farmers` collection |
| **UI** | ⚠️ Missing back button. Progress indicator exists. |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Data saves but UX incomplete |
| **Known Issues** | D-01 (no back button), D-02 (premature wizard_complete flag) — Sprint 1 fixes pending |
| **Overall** | ⚠️ Partial |

---

## 4. Dashboard

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Central hub for profile, scheme recommendations, alerts, and navigation |
| **Backend** | ✅ `GET /api/farmers/me` returns full profile with recommendations and alerts |
| **Frontend** | ⚠️ Large component (1165 lines). Multiple dead nav items. Crop Recommendation conditionally hidden. |
| **API** | ✅ `GET /api/farmers/me` |
| **Database** | ✅ |
| **UI** | ⚠️ Crop Recommendation not visible to all users. Some sidebar items are dead ends. |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Core layout works; multiple dead paths |
| **Known Issues** | Dead nav buttons, hidden crop rec, missing loading skeleton, no empty state |
| **Overall** | ⚠️ Partial |

---

## 5. Scheme Recommendation

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Match farmer profile to eligible government schemes |
| **Backend** | ✅ `RecommendationService.get_recommendations()` |
| **Frontend** | ✅ Shown in Dashboard "Scheme Recommendations" tab |
| **API** | ✅ Returned as part of `GET /api/farmers/me` |
| **Database** | ✅ Scheme rules in policy engine |
| **UI** | ✅ Card-based display |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ✅ |
| **Known Issues** | Hardcoded scheme rules. No real-time portal scraping. |
| **Overall** | ✅ Working |

---

## 6. Crop Recommendation

| Attribute | Detail |
|-----------|--------|
| **Purpose** | ML-based crop recommendation using soil type and season |
| **Backend** | ✅ `POST /api/farmers/recommend-crop` — `CropRecommender` ML model |
| **Frontend** | ⚠️ UI exists but is conditionally hidden |
| **API** | ✅ `POST /api/farmers/recommend-crop` |
| **Database** | N/A — stateless ML inference |
| **UI** | ⚠️ Not prominently surfaced to users |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ✅ Backend works; UI discoverability poor |
| **Known Issues** | B-01 — visibility fix needed in Sprint 1 |
| **Overall** | ⚠️ Backend complete, UX incomplete |

---

## 7. OCR Document Upload (Aadhaar / PAN)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Upload Aadhaar/PAN cards; OCR extracts fields to autofill profile |
| **Backend** | ✅ `POST /api/upload` — `pipeline.py` → `parsers.py` → `mapping.py` → `validation.py` |
| **Frontend** | ✅ Upload UI in Dashboard |
| **API** | ✅ `POST /api/upload` multipart form data |
| **Database** | ✅ Saves extracted fields + raw text to `documents` collection |
| **UI** | ⚠️ No progress bar, no manual correction UI, no confidence display |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Pipeline works but accuracy varies |
| **Known Issues** | C-01 (age calc) ✅ Fixed. C-02 (DOB cap) ✅ Fixed. Preprocessing/regex/correction: Sprint 2. |
| **Overall** | ⚠️ Functional but needs Sprint 2 improvements |

---

## 8. Community Forum

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Discussion board for farmers to share experiences |
| **Backend** | ✅ `app/api/stories.py` — CRUD for posts |
| **Frontend** | ✅ Community section in Dashboard sidebar |
| **API** | ✅ `GET/POST /api/stories` |
| **Database** | ✅ `stories` collection in MongoDB |
| **UI** | ⚠️ Basic list display; no rich text, no threading |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ✅ Core CRUD works |
| **Known Issues** | No moderation. No pagination. No empty state. |
| **Overall** | ⚠️ Basic functionality works |

---

## 9. Predictive Alerts

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Rule-based alerts for upcoming deadlines and eligibility events |
| **Backend** | ✅ `PredictiveAlertService.generate_alerts()` |
| **Frontend** | ✅ Displayed in Dashboard |
| **API** | ✅ Returned as part of `GET /api/farmers/me` |
| **Database** | N/A — computed on the fly |
| **UI** | ⚠️ Alert cards shown but minimal styling |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ✅ |
| **Known Issues** | Rules are static/hardcoded. No real-time triggers. |
| **Overall** | ✅ Working |

---

## 10. Navigation (Sidebar + Navbar)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Allow users to navigate between app sections |
| **Backend** | N/A |
| **Frontend** | ⚠️ Several sidebar items (Analytics, Settings, Help) are dead ends. Navbar auth state breaks on same-tab login. |
| **API** | N/A |
| **Database** | N/A |
| **UI** | ⚠️ Visually present; functionally incomplete |
| **Integrated** | ⚠️ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Basic navigation works; dead buttons exist |
| **Known Issues** | A-01 (Navbar auth state), dead nav links — Sprint 1 |
| **Overall** | ⚠️ Partial |

---

## 11. Multilingual Support (i18n)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Support English and Hindi for farmer accessibility |
| **Backend** | N/A |
| **Frontend** | ✅ `react-i18next` configured. Language selector in Navbar. |
| **UI** | ⚠️ Some strings hardcoded in English |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Toggle works but coverage incomplete |
| **Known Issues** | Several hardcoded English strings in Dashboard.tsx |
| **Overall** | ⚠️ Partial |

---

## 12. Dark Mode

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Theme toggle for user comfort |
| **Backend** | N/A |
| **Frontend** | ✅ Tailwind dark mode classes throughout |
| **UI** | ✅ |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ✅ |
| **Known Issues** | None |
| **Overall** | ✅ Working |

---

## 13. Scheme Monitor (Background Scraping)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Background task to scrape government scheme portals for updates |
| **Backend** | ⚠️ `scheme_monitor.py` — uses `print()` for logging (Sprint 4 fix) |
| **Frontend** | ✅ Manual trigger button in Dashboard |
| **API** | ✅ `POST /api/monitoring/trigger-scheme-monitor` |
| **Database** | N/A |
| **UI** | ⚠️ Loading toast exists but result display minimal |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Basic scraping works; reliability unknown |
| **Known Issues** | `print()` in scheme_monitor.py (Sprint 4). No retry logic. |
| **Overall** | ⚠️ Partial |

---

## 14. Policy Ingestor (AI Document Analysis)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Ingest policy PDF/text documents via AI to extract scheme rules |
| **Backend** | ✅ `policy_ingestor.py` in ML pipeline |
| **Frontend** | ✅ Upload UI with "Policy" type option |
| **API** | ✅ `POST /api/monitoring/test/policy-ingest` |
| **Database** | ⚠️ Rules in memory/file only; no persistent DB record |
| **UI** | ✅ Loading toast + result count shown |
| **Integrated** | ✅ |
| **Tested** | ⚠️ Manual only |
| **Working** | ⚠️ Runs but accuracy not measured |
| **Known Issues** | No persistence. Console.log removed (Sprint 1 ✅). |
| **Overall** | ⚠️ Experimental |

---

## Summary Table

| Feature | Backend | Frontend | Integrated | Working |
|---------|---------|----------|-----------|---------|
| Authentication | ✅ | ⚠️ | ✅ | ⚠️ |
| Session / Protected Routes | ✅ | ⚠️ | ✅ | ⚠️ |
| Profile Wizard | ✅ | ⚠️ | ✅ | ⚠️ |
| Dashboard | ✅ | ⚠️ | ✅ | ⚠️ |
| Scheme Recommendation | ✅ | ✅ | ✅ | ✅ |
| Crop Recommendation | ✅ | ⚠️ | ✅ | ⚠️ |
| OCR Upload | ✅ | ✅ | ✅ | ⚠️ |
| Community Forum | ✅ | ✅ | ✅ | ✅ |
| Predictive Alerts | ✅ | ✅ | ✅ | ✅ |
| Navigation | N/A | ⚠️ | ⚠️ | ⚠️ |
| i18n / Multilingual | N/A | ⚠️ | ✅ | ⚠️ |
| Dark Mode | N/A | ✅ | ✅ | ✅ |
| Scheme Monitor | ⚠️ | ✅ | ✅ | ⚠️ |
| Policy Ingestor | ⚠️ | ✅ | ✅ | ⚠️ |
