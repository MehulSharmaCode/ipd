# AgriSense: Master Technical Documentation

*Prepared by: Chief Software Architect / Technical Reviewer*

## 1. Executive Summary & Project Overview
AgriSense is an intelligent, scalable, and secure platform designed to bridge the gap between Indian farmers and the complex landscape of agricultural government schemes. The core problem AgriSense solves is the low adoption rate of beneficial schemes due to complex eligibility criteria, cumbersome documentation, and lack of awareness. 

AgriSense provides a unified ecosystem where a farmer can simply upload their identity (Aadhaar, PAN) and land records (Maharashtra 7/12 Satbara). The platform uses an **Intelligent Document Processing (IDP) Engine** powered by OCR (Tesseract) and Vision LLMs (Google Gemini 1.5 Flash) to auto-extract, normalize, and validate all necessary agricultural parameters. These parameters construct a comprehensive `FarmerProfile`. 

This profile is then fed into an advanced **Recommendation Engine** that filters eligible schemes using a YAML-based Rules Engine, predicts success probabilities using ML inference models, and utilizes a **Knowledge Graph** to compute the Maximum Weight Independent Set (MWIS), ultimately generating optimal "bundles" or packages of mutually compatible schemes.

## 2. High-Level Architecture & Tech Stack

AgriSense operates on a modern, decoupled client-server architecture:

*   **Frontend (Client Layer):** React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion for animations. Uses Axios for API communication and React Router for declarative navigation.
*   **Backend (API Layer):** FastAPI (Python 3.10+) providing high-performance, asynchronous RESTful APIs.
*   **Database (Persistence Layer):** MongoDB, accessed asynchronously via `motor`.
*   **Intelligent Document Processing (IDP) Layer:**
    *   **Tesseract OCR:** For structured ID cards (Aadhaar, PAN).
    *   **Google Gemini 1.5 Flash API:** For unstructured, localized, and complex documents like the Marathi 7/12 land record.
*   **Machine Learning / Logic Layer:**
    *   **Scikit-Learn (Mocked Inference):** `SchemeSuccessPredictor` and `BenefitPredictor` for ML scoring.
    *   **NetworkX:** For Knowledge Graph construction and bundle optimization (MWIS).
    *   **PyYAML:** For maintaining dynamic scheme eligibility rules.

### Macro Architecture Flow
`Client (React)` ↔ `FastAPI Router` ↔ `Services & Engines (IDP, Rules, ML)` ↔ `MongoDB`

---

## 3. End-to-End User Journey

1.  **Onboarding & Authentication:** User lands on the animated Landing Page, registers, and authenticates via JWT.
2.  **Profile Wizard (Document Intake):**
    *   **Step 1:** Uploads Aadhaar and PAN. The backend OCR extracts Name, DOB, Gender, and ID numbers.
    *   **Step 2:** Uploads 7/12 Land Record. The backend Gemini Vision API extracts farm size, soil type, crops, and irrigation methods.
    *   **Step 3:** Reviews the auto-filled `FarmerProfile`. Fields extracted by AI are explicitly tagged in the UI. User confirms and saves.
3.  **Dashboard (The Hub):**
    *   The farmer lands on a comprehensive dashboard displaying their land statistics and verified status.
    *   The backend triggers the **Recommendation Engine** asynchronously or on-demand.
    *   The user is presented with **Top Recommended Bundles** (compatible scheme packages) and individual highly-rated schemes.
4.  **Proactive Monitoring & Alerts:** The dashboard displays real-time risk alerts (weather/pests based on crop and state) and new scheme updates scraped from government portals.
5.  **Community Hub (Social Proof):** Users can read success stories from other farmers, filtered by crop or region, encouraging scheme adoption.

---

## 4. Frontend Architecture (React, UI/UX)

The frontend is a Single Page Application (SPA) designed with a "premium, modern, and trustworthy" aesthetic.

### Key Directories
*   `src/pages/`: Contains monolithic view components (`LandingPage.tsx`, `AuthPage.tsx`, `ProfileWizard.tsx`, `Dashboard.tsx`, `CommunityHub.tsx`).
*   `src/components/`: Reusable UI components (`ProtectedRoute.tsx`, `LanguageSwitcher.tsx`), and the `ui/` folder containing shadcn/ui base primitives.
*   `src/lib/api.ts`: Centralized Axios client with request (JWT attachment) and response (auto-logout on 401) interceptors.

### UX/UI Design Principles
*   **Glassmorphism & Gradients:** Heavy use of backdrop-blur, subtle borders, and emerald/teal gradient meshes to convey a modern, "agri-tech" feel.
*   **Micro-interactions:** Framer Motion is used for layout transitions, stagger animations, and floating accents (e.g., the glowing orbs in the background).
*   **Progressive Disclosure:** The `ProfileWizard` hides complex form fields behind a step-by-step document upload process, heavily reducing cognitive load.

---

## 5. Backend Architecture (FastAPI, Modular Monolith)

The backend follows a domain-driven, modular monolith pattern, ensuring clear separation of concerns.

### Directory Structure (`backend/app/`)
*   `api/`: Route definitions (`auth.py`, `farmers.py`, `upload.py`, etc.).
*   `core/`: Configuration (`config.py`), Database connection (`database.py`), Security/JWT (`security.py`).
*   `models/`: Pydantic schemas for request/response validation and DB serialization (`farmer.py`, `story.py`).
*   `document_processing/`: The IDP Engine (Router, OCR, Vision, Normalizer, Validator).
*   `ml/`: The intelligence layer containing the feature store, inference models, rules engine, and knowledge graph.
*   `services/`: Business logic like `predictive_alert_service.py` and `scheme_monitor.py`.

The application relies on FastAPI's Dependency Injection (`Depends`) to pass database clients and the current authenticated user to route handlers.

---

## 6. Intelligent Document Processing (IDP) Engine Architecture

The IDP Engine is the crown jewel of AgriSense data ingestion. It guarantees that data entering the database is structured, canonical, and validated.

**Pipeline Flow:**
`Upload` → `DocumentRouter` → `Processor (OCR/Vision)` → `ExtractionResult` → `SemanticNormalizer` → `DocumentValidator` → `FarmerProfileBuilder`

*   **DocumentRouter (`router.py`):** A module-level singleton registry. It takes the `doc_type` and routes the file to the registered processor. This satisfies the Open/Closed Principle (easy to add new document types).
*   **Interfaces (`interfaces.py`):** Defines a `DocumentProcessor` structural protocol utilizing Python's `typing.Protocol`.
*   **ExtractionResult:** A standardized Pydantic schema enforcing a uniform output structure (`fields`, `validation`, `metadata`) regardless of the processor used.

---

## 7. OCR Pipeline (Tesseract)

Used for highly structured, predictable documents.

*   **AadhaarProcessor / PANProcessor:** Wrap `pytesseract` and OpenCV.
*   **Pipeline:** Image preprocessing (grayscale, thresholding, deskewing) → Tesseract string extraction → Regex/Heuristic parsing.
*   **Data Extracted:** `full_name`, `dob`, `gender`, `aadhar_number`, `pan_number`.

---

## 8. Vision Pipeline (Gemini 1.5 Flash)

Used for the Maharashtra 7/12 Satbara, a highly unstructured, regional (Marathi), handwritten/typed hybrid document.

*   **GeminiClient (`vision/gemini_client.py`):** A wrapper around the Google GenAI SDK. Sends the image as a base64 encoded payload along with a highly tuned prompt.
*   **Prompts (`vision/prompts.py`):** Instructs the LLM to act as a land revenue expert, enforcing strict JSON output for specific keys (survey_number, land_area, irrigation, soil_type, current_crop) and penalizing hallucinations.

---

## 9. Semantic Normalization Layer

Because OCR and LLMs produce varied text strings (e.g., "Well irrigation", "MALE", "Black cotton soil"), these values cannot be directly used by the Rules Engine.

*   **`SemanticNormalizer` (`document_processing/normalizer.py`):** A middleware layer inserted *after* extraction.
*   It utilizes robust mapping dictionaries to map diverse natural language outputs into strict, canonical internal enums expected by the frontend and the ML engines.
    *   *Example:* `"Well irrigation"` → `"Well"`
    *   *Example:* `"MALE"` → `"Male"`
    *   *Example:* `"Rain-fed agriculture"` → `"Rain"`

---

## 10. Document Validation Engine

Validates the *logical consistency* of the extracted data.

*   **`DocumentValidator` (`document_processing/validator.py`):**
    *   Checks if the Aadhaar number passes a checksum/regex.
    *   Cross-references names (e.g., does the name on the PAN card vaguely match the name on the Aadhaar card using string similarity?).
    *   Flags warnings if the 7/12 document seems to belong to a completely different person.

---

## 11. Farmer Profile Builder & State Management

The frontend maintains a `ProfileState`. As documents are uploaded, the `mapExtractionToProfile` utility incrementally updates this state. 
On the backend, `FarmerProfileBuilder` takes disparate `ExtractionResult` objects, merges them, handles conflict resolution (e.g., if two documents have different DOBs), and outputs a clean `FarmerUpdate` Pydantic model for database persistence.

---

## 12. Recommendation Engine Architecture

The recommendation system transforms a static profile into actionable intelligence.

**Flow:**
`FarmerProfile` → `FeatureStore` → `RulesEngine` (Filtering) → `RankingEngine` (Scoring) → `KnowledgeGraph` (Bundling)

1.  **Feature Store:** Translates raw profile data (e.g., `age: 35`, `land: 1.5`) into numerical/boolean feature vectors suitable for ML and Rules evaluation.

---

## 13. Rules Engine & Eligibility Calculation

*   **Source of Truth:** `ml/rules/schemes_rules.yaml`. Defines schemes, their attributes (benefit type, max value), and their strict eligibility conditions (age bounds, max land, required crops, states, etc.).
*   **`SchemeRulesEngine` (`ml/rules/engine.py`):** Evaluates a farmer's Feature Vector against the YAML rules dynamically. If a farmer fails a condition, they are placed in `ineligible_schemes` with a precise explanation of *why* (e.g., "Land size exceeds 2.0 Ha").

---

## 14. Machine Learning Integrations (Predictors)

For schemes that pass the Rules Engine, they are scored.

*   **`SchemeSuccessPredictor`:** Uses a (mocked) `RandomForestClassifier` to predict the probability (0.0 to 1.0) of the farmer successfully obtaining the scheme, based on historical feature vectors.
*   **`BenefitPredictor`:** Uses a (mocked) `GradientBoostingRegressor` to estimate the actual financial value the farmer will receive from the scheme, factoring in farm size and region.

---

## 15. Knowledge Graph & Scheme Bundling (MWIS)

Farmers usually benefit most from applying to *multiple* schemes, but some schemes are mutually exclusive (e.g., you cannot claim a state tractor subsidy and a central tractor subsidy simultaneously).

*   **`KnowledgeGraph` (`ml/graph/knowledge_graph.py`):** 
    *   Uses `NetworkX`.
    *   Nodes = Eligible Schemes.
    *   Node Weights = `Predicted Financial Value * Success Probability`.
    *   Edges = Conflicts / Mutual Exclusivity between schemes.
*   **Optimization:** The graph calculates the **Maximum Weight Independent Set (MWIS)**. This algorithm mathematically guarantees the bundle of schemes that yields the absolute highest expected financial return *without* any conflicts.

---

## 16. Predictive Alerts & Monitoring Subsystem

*   **`PredictiveAlertService`:** Generates localized, heuristic-based alerts. E.g., If the farmer is in Maharashtra and grows Onion, it generates a "Unseasonal Rain / Harvest Early" alert.
*   **`SchemeMonitor`:** A background task system that scrapes (mocked) government portals to notify users of new schemes or impending deadlines.
*   **`PolicyIngestor`:** An AI pipeline (simulated) where admins can upload PDF policies, and the system extracts rules to append to the YAML configuration.

---

## 17. Database Schema & Data Models (MongoDB)

Using MongoDB allows flexible schema evolution. Key collections:

*   **`farmers`**: 
    *   Identity: `email`, `hashed_password`, `full_name`, `is_verified`
    *   Agricultural: `state`, `land_size_hectares`, `primary_crops`, `irrigation_type`
    *   App State: `is_aadhar_verified`, `is_pan_verified`, `profile_wizard_complete`
*   **`stories`**:
    *   `farmer_id`, `farmer_name`, `content`, `crop_type`, `upvotes`
*   **`schemes`**: (Primarily managed via YAML currently, but structured for DB migration).

---

## 18. API Documentation & Routing

Standard RESTful endpoints documented automatically via FastAPI's Swagger UI (`/docs`).

*   `POST /api/auth/signup` & `POST /api/auth/login`: Issues OAuth2 JWT tokens.
*   `POST /api/upload`: The unified IDP ingestion endpoint. Expects `multipart/form-data` with `file` and `doc_type`.
*   `GET /api/farmers/me`: Returns the current profile.
*   `PUT /api/farmers/me`: Updates the profile.
*   `GET /api/farmers/me/recommendations`: Triggers the entire ML/Graph pipeline and returns `recommended_bundles`, `recommended_schemes`, and `ineligible_schemes`.
*   `GET /api/stories`: Community hub endpoints.

---

## 19. Security, Auth & Compliance

*   **Authentication:** JWT (JSON Web Tokens) generated using `python-jose`, signed with HS256. Passwords hashed using `bcrypt` (via `passlib`).
*   **Authorization:** The `get_current_user` dependency protects sensitive routes, ensuring a farmer can only access their own data.
*   **Data Privacy:** Uploaded documents are saved temporarily to disk for processing and can be configured for immediate deletion post-extraction to comply with PII regulations.
*   **API Resilience:** Axios interceptors on the frontend handle automatic logout upon token expiration (401 Unauthorized), preventing UI desyncs.

---

## 20. Key Architectural Design Decisions & Justifications

1.  **Decoupling Extraction from Normalization:** By keeping `Processor` strictly for raw extraction and `SemanticNormalizer` for data cleaning, we can swap out the OCR engine (e.g., moving from Tesseract to AWS Textract) without rewriting any business logic or mapping rules.
2.  **Using LLMs for Regional Land Records:** Traditional OCR fails on Marathi 7/12 records due to layout complexity and handwriting. Gemini 1.5 Flash Vision handles contextual spatial understanding natively, achieving high accuracy with a simple prompt.
3.  **YAML for Scheme Rules:** Hardcoding rules in Python requires deployments for every policy change. YAML allows non-engineers (domain experts) to update scheme eligibility safely.
4.  **Graph Theory for Bundling (MWIS):** Standard sorting by probability doesn't account for mutual exclusivity. Using a graph guarantees optimal combinations, solving a complex NP-hard problem elegantly for the user.

---

## 21. System Advantages, Limitations & Future Scope

**Advantages:**
*   **Frictionless UX:** Replaces 50-field forms with 2 document uploads.
*   **Highly Extensible:** New document types can be added by implementing one Protocol interface.
*   **Intelligent Routing:** Doesn't just list schemes; it explains *why* a user was selected or rejected, and mathematically optimizes bundles.

**Limitations:**
*   Currently, the ML models (`RandomForest`, `GradientBoosting`) are mocked using synthetic weights. They require training on real historical disbursement data.
*   OCR relies on Tesseract, which struggles with low-light/blurry mobile captures.

**Future Scope:**
*   **Regional Language UI:** Integrate `i18next` deeply to allow the entire UI to switch to Marathi/Hindi.
*   **Voice Inputs:** Expand the experimental `useVoiceInput` hook to allow illiterate farmers to fill missing fields by speaking.
*   **RAG Chatbot:** Integrate a conversational agent allowing farmers to ask specific questions about their recommended schemes.

---

## 22. Interactive Demo Script & Workflow Guide

*For live presentations or investor pitches.*

1.  **Start at the Landing Page:** Highlight the modern UI, statistics, and smooth animations. Emphasize the mission to simplify agri-schemes.
2.  **Registration:** Create a new account. Show how they land on the `ProfileWizard`.
3.  **Step 1 (Identity):** Upload a sample Aadhaar Card. Wait for the green success toast. Explain that OCR extracted the ID locally. Upload a PAN card. Show the "Continue" button unlocking.
4.  **Step 2 (Land Record):** Upload a sample 7/12 document. Mention this hits a Vision LLM to parse complex Marathi data. Point out the blue "Extracted Information" summary box detailing the farm size and soil type.
5.  **Step 3 (Review):** Show the populated form. Explicitly point out the "AI Extracted" badges next to fields like Land Size and Soil Type. Save the profile.
6.  **Dashboard:** The user is redirected to the Dashboard. The ML engine runs. Scroll down to show the **Top Recommended Bundle**. 
7.  **Explain the Intelligence:** Point out the explanation texts (Why you were selected) and the Expected Financial Impact. Switch to the "Explore Other Schemes" tab to show exactly *why* certain schemes were rejected.
8.  **Community & Alerts:** Briefly show the Risk Alerts tab (e.g., Weather warnings) and navigate to the Community Hub to demonstrate social proof.

---

## 23. Viva / Technical Review Preparation (Top Questions)

### Architecture & Design
1. **Q: Why did you choose FastAPI over Django/Flask?**
   *A:* FastAPI provides native async support, which is critical when making I/O bound calls to the Gemini API and MongoDB. It also auto-generates Swagger documentation and uses Pydantic for robust data validation.
2. **Q: Explain the Document Processing Engine pipeline.**
   *A:* Upload → DocumentRouter → Processor (OCR/Vision) → ExtractionResult → SemanticNormalizer → DocumentValidator → ProfileBuilder.
3. **Q: How do you handle a new document type being introduced?**
   *A:* We implement a new class following the `DocumentProcessor` protocol, register it in the `DocumentRouter` with a unique key, and update the `DOC_TYPE_MAP` on the frontend. No existing pipeline code needs to change.

### Frontend Integration
4. **Q: How does the frontend know which fields were extracted by AI?**
   *A:* The backend returns an `ExtractionResult` which maps fields. The frontend `mapExtractionToProfile` function tracks which specific keys were populated from the 7/12 document and adds them to an `aiFilledFields` Set, which triggers the UI badges.
5. **Q: How do you handle JWT expiration?**
   *A:* An Axios response interceptor globally catches `401 Unauthorized` errors, clears the local storage, and securely redirects the user to the login page.

### AI & Machine Learning
6. **Q: Why use Gemini Vision for 7/12 records instead of Tesseract?**
   *A:* 7/12 records are unstructured, often handwritten, in Marathi, and have complex spatial tables. Tesseract yields chaotic text blocks. Gemini understands the spatial layout and extracts semantic meaning (e.g., mapping a specific column to "Irrigation Type").
7. **Q: What is Semantic Normalization and why is it needed?**
   *A:* LLMs and OCR return varied string outputs ("Male", "MALE", "Well Irrigation"). The Rules Engine requires strict enums. The Normalizer maps diverse outputs into canonical internal states.
8. **Q: Explain how the Knowledge Graph bundles schemes.**
   *A:* It models schemes as nodes and conflicts as edges. By calculating the Maximum Weight Independent Set (MWIS), it finds the combination of schemes that have no conflicts but yield the highest combined financial benefit.

### Data & Security
9. **Q: How is data validated before hitting the database?**
   *A:* Twice. First, the `DocumentValidator` performs logical checks on the extracted data. Second, FastAPI automatically validates incoming payloads against Pydantic schemas (`FarmerUpdate`) before MongoDB insertion.
10. **Q: How do you ensure the MongoDB database scales?**
    *A:* We use asynchronous drivers (`motor`). Future scaling involves indexing critical fields (like `email` and `state`) and potentially sharding based on geographic regions if the dataset grows massive.

*(End of Document)*
