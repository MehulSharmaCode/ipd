# DECISIONS.md — Engineering Decisions
> **Last Updated:** 2026-07-21 | Cross-reference: ARCHITECTURE.md

---

## Decision 1: FastAPI over Django/Flask

**Decision:** Use FastAPI as the backend framework.

**Reason:**
- Native async support via Motor (MongoDB async driver)
- Automatic OpenAPI/Swagger docs generation
- Native Pydantic integration for request/response validation
- Excellent performance for a hackathon-scale project
- Type hints throughout → IDE-friendly development

**Alternatives Rejected:**
- **Django REST Framework**: Too heavy, sync-first, less type-safe
- **Flask**: Minimal but no built-in validation, no async native support, requires more boilerplate

---

## Decision 2: MongoDB over PostgreSQL/MySQL

**Decision:** Use MongoDB as the primary database.

**Reason:**
- Flexible schema — farmer profiles have many optional fields that vary significantly by user
- No migration overhead — schema evolves by adding fields to Pydantic models
- Motor provides native async support for FastAPI
- Document model matches the farmer profile structure naturally

**Alternatives Rejected:**
- **PostgreSQL**: Schema changes require migrations; optional field management is awkward; overkill for this scale
- **SQLite**: No production scalability, no native async support

**Trade-offs:**
- No referential integrity (farmer_id in stories is just a string)
- No complex joins — but this project doesn't need them
- No unique index enforced at DB level for email (application-level only)

---

## Decision 3: YAML Rules Engine over Pure ML

**Decision:** Use a declarative YAML rules engine as a hard gate before ML scoring.

**Reason:**
- Government scheme eligibility criteria are explicit and binary (not probabilistic)
- Hard rules (age < 60, land < 2 hectares) can be validated deterministically
- YAML rules are human-readable and maintainable without ML expertise
- Prevents ML model from recommending clearly ineligible schemes
- Enables clear explanation ("You're ineligible because land_size > 2 ha")

**Alternatives Rejected:**
- **Pure ML classification**: Black-box decisions; difficult to explain; might hallucinate eligibility
- **Database-stored rules**: More complex to update; YAML is version-controlled

---

## Decision 4: NetworkX MWIS for Scheme Bundling

**Decision:** Model scheme conflicts as a graph and use Maximum Weight Independent Set (MWIS) via NetworkX clique-finding on the complement graph.

**Reason:**
- Government schemes have conflict relationships (e.g., PM Kisan + Small Farmer Support cannot be combined)
- MWIS finds all valid non-conflicting scheme combinations
- Ranking bundles by total financial value provides a natural priority order
- NetworkX provides ready-made `find_cliques()` implementation (complement approach)
- Demonstrates academic graph theory application

**Algorithm:**
1. Build scheme graph with conflict edges
2. For eligible schemes only — extract subgraph
3. Compute complement graph (edges between non-conflicting nodes)
4. Find all cliques in complement (= independent sets in original)
5. Each clique = a valid bundle; rank by total benefit value

**Alternatives Rejected:**
- **Simple filtering**: Only removes direct conflicts; misses multi-way conflicts
- **ILP solver**: More powerful but overkill for 10 schemes; adds heavy dependency
- **Greedy heuristic**: Does not guarantee optimal bundles

---

## Decision 5: Tesseract OCR over Cloud Vision APIs

**Decision:** Use Tesseract (local) for OCR rather than Google Cloud Vision, AWS Textract, or Azure OCR.

**Reason:**
- No API costs for a hackathon project
- Works offline/locally without internet
- Sufficient accuracy for printed ID card text
- pytesseract wraps Tesseract cleanly with Python

**Alternatives Rejected:**
- **Google Cloud Vision API**: Excellent accuracy but costs money per call; requires GCP setup
- **AWS Textract**: Similar cost issue; heavy AWS dependency
- **EasyOCR**: Open source, multilingual, but slower than Tesseract for clean scanned images

**Trade-offs:**
- No multilingual OCR (Hindi script on cards not extracted)
- Requires Tesseract installation on server OS (complicates deployment)
- Lower accuracy on degraded/photo images vs cloud APIs

---

## Decision 6: Multi-Strategy Tesseract Detection

**Decision:** Implement a 4-strategy Tesseract path detection system in `ocr/config.py`.

**Reason:**
- macOS development (Apple Silicon vs Intel Homebrew different paths)
- CI/CD environments don't inherit shell PATH
- Docker containers may have non-standard paths
- Eliminates "Tesseract not found" errors across different machines

**Strategies (in priority order):**
1. `TESSERACT_PATH` env var (explicit override)
2. `shutil.which("tesseract")` with augmented PATH (adds Homebrew dirs)
3. Known platform defaults (macOS/Linux/Windows)
4. Detailed diagnostic error

---

## Decision 7: JWT in localStorage (not HttpOnly Cookies)

**Decision:** Store JWT in `localStorage` (not HttpOnly cookies).

**Reason:**
- Simpler implementation for hackathon scope
- Frontend SPA can easily access token for Axios interceptor
- No CSRF concerns with localStorage + manually attached headers

**Trade-offs:**
- XSS vulnerability: malicious scripts could read localStorage token
- **Production recommendation**: Migrate to HttpOnly + SameSite=Strict cookies + short-lived access tokens + refresh token rotation

---

## Decision 8: Hardcoded CORS Origins

**Decision:** CORS origins are hardcoded in `main.py` (localhost:5173, 5174, 5175).

**Reason:**
- Hackathon project; Vite dev server uses port 5173 by default
- Port range covers port changes during development

**Trade-offs:**
- Not production-ready
- Must update manually if port changes

**Future:** Move to environment variable: `CORS_ORIGINS=http://localhost:5173,https://app.agrisense.com`

---

## Decision 9: Denormalized Author Info in Stories

**Decision:** Store `farmer_name` directly in the `stories` collection (denormalized).

**Reason:**
- Avoids join/lookup on every story fetch
- MongoDB doesn't support native joins natively (requires `$lookup`)
- Name rarely changes after profile creation

**Trade-offs:**
- If farmer updates name, old stories still show old name
- No consistency guarantee

---

## Decision 10: Pydantic `exclude_unset=True` for Profile Updates

**Decision:** Use `model_dump(exclude_unset=True)` for `PUT /api/farmers/me`.

**Reason:**
- Profile wizard sends data in steps — each step should only update its own fields
- Prevents accidentally overwriting data from previous steps with null/default values
- Mirrors MongoDB `$set` semantics

---

## Decision 11: Computed Recommendations (Not Stored)

**Decision:** `recommended_schemes`, `recommended_bundles`, `ineligible_schemes`, `predictive_alerts` are computed on every `GET /api/farmers/me` — not stored in MongoDB.

**Reason:**
- Recommendations must be fresh (rules + ML model can be updated server-side)
- Storing stale recommendations creates consistency issues
- Simpler architecture for MVP

**Trade-offs:**
- Expensive — ML inference + graph computation on every profile fetch
- Should be cached (Redis/in-memory) for production scale

---

## Decision 12: React 19 + Vite + TailwindCSS

**Decision:** Use React 19, Vite 7, TailwindCSS for frontend.

**Reason:**
- Vite offers instant HMR and fast builds
- React 19 is the latest stable with new concurrent features
- TailwindCSS provides rapid UI development without custom CSS

**Alternatives Rejected:**
- **Next.js**: SSR overhead unnecessary for a SPA; adds complexity
- **Vue/Svelte**: Team familiarity with React
- **CSS Modules / Styled Components**: Slower development for hackathon pace

---

## Decision 13: Shadcn/UI for Components

**Decision:** Use Shadcn/UI (Radix UI primitives + TailwindCSS) for UI components.

**Reason:**
- Copy-into-project pattern (no runtime library) — full control
- Built on accessible Radix UI primitives
- Excellent TailwindCSS integration
- Beautiful dark mode support

---

## Decision 14: i18next for Internationalization

**Decision:** Use i18next with react-i18next for multi-language support.

**Reason:**
- Industry standard for React i18n
- Lazy loading of locale files (performance)
- Browser language auto-detection
- Supports all 4 required languages (en, hi, mr, gu)

---

## Decision 15: LightGBM for Scheme Success Model

**Decision:** Use LightGBM for the scheme approval probability model.

**Reason:**
- Fast inference (important for per-request ML)
- Small model size (~1MB serialized)
- Handles categorical features natively
- Compatible with scikit-learn pipeline (joblib serialization)
- Better than deep learning for tabular data at this scale

**Alternatives Rejected:**
- **PyTorch neural network**: Overkill for tabular data; larger model size
- **Decision Tree**: Lower accuracy; no probability output
- **Logistic Regression**: Cannot capture feature interactions
