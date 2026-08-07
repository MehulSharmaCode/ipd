# Frontend Architecture Audit

## 1. Project Overview & Architecture
- **Framework**: React + Vite (Typescript)
- **State Management**: React state hooks (`useState`, `useEffect`), React Router (`react-router-dom`) for navigation, and `localStorage` for JWT persistence.
- **Styling**: Tailwind CSS + `shadcn/ui` components.
- **Service Layer**: Axios instance in `src/lib/api.ts` with request interceptors (attaches `access_token`) and response interceptors (handles 401 unauth / token invalidation).
- **Core Pages**:
  - `App.tsx`: Sets up routing and Contexts (Theme).
  - `LandingPage.tsx`: Public introduction.
  - `AuthPage.tsx`: Handles login and registration.
  - `ProfileWizard.tsx`: Multi-step onboarding to collect personal details and OCR documents (currently hardcoded for Aadhaar and PAN).
  - `Dashboard.tsx`: Main farmer interface to view matching schemes and manage profile/documents.

## 2. API Contract & Mismatches Found
The backend's `ExtractionResult` returning standard `data.fields.<field>.value` was safely mapped in the `upload.py` backend endpoint to preserve the legacy `aadhaarNumber` and `panNumber` strings inside `fields`, so basic Aadhaar and PAN extraction won't break on the frontend.
However, **there are gaps and mismatches for the new 7/12 Gemini integration**:
1. **Frontend `Dashboard.tsx` Document Upload Type Mismatch**:
   - `Dashboard.tsx` uses a dropdown where Land Record is value `Land_Record`. 
   - `handleDocumentUpload` does `docData.append('doc_type', uploadType.toLowerCase())`, which sends `"land_record"`.
   - **Backend Mismatch**: The backend router registers `Satbara712Processor` as `"7_12"`. It will return a 400 Unsupported Document Type.
2. **`ProfileWizard.tsx` Lacks 7/12 Onboarding**:
   - The onboarding wizard (`ProfileWizard.tsx`) strictly handles `aadhar` and `pan`.
   - It needs to be extended to support a step for 7/12 Land Record upload to extract the farmer's agricultural details (land size, irrigation, crop season, etc.).
3. **Missing Agricultural Auto-Fill logic in `Dashboard.tsx`**:
   - When a user uploads a document via the Dashboard, only `fields.aadhaarNumber` and `fields.panNumber` are handled for ID extraction.
   - The Dashboard does not automatically pull Gemini's agricultural fields (e.g. `land_size_hectares`, `primary_crops`) into the form state after a `Land_Record` upload.

## 3. Component Impact Analysis (CIA)
| Component | Status | Required Changes |
| :--- | :--- | :--- |
| `src/lib/api.ts` | 🟢 SAFE | None. The interceptors handle auth perfectly. |
| `src/pages/AuthPage.tsx` | 🟢 SAFE | None. Registration flow remains identical. |
| `src/pages/ProfileWizard.tsx` | 🟠 NEEDS MODIFICATION | Add a 7/12 document upload step. Parse the new Gemini agricultural fields from the `/upload` API response and auto-fill the state (`land_size_hectares`, `irrigation_type`, etc.). |
| `src/pages/Dashboard.tsx` | 🟠 NEEDS MODIFICATION | Fix the `doc_type` mismatch (`land_record` vs `7_12`). Update `handleDocumentUpload` to auto-fill the profile form when agricultural details are successfully extracted. |
| `src/components/ProtectedRoute.tsx`| 🟢 SAFE | Checks for `profile_wizard_complete` or `is_aadhar_verified && is_pan_verified`. It works fine as-is, though we may want it to also check `is_712_verified` later if it becomes mandatory. |

## 4. Security & QA Readiness
- **Token Handling**: Standard implementation using `localStorage`. Interceptors correctly clear tokens and redirect to `/login` on `401 Unauthorized`.
- **Form Data Validation**: Relies mostly on backend validation, but basic types (parseInt, parseFloat) are handled properly before submission.
- **Performance**: High. File sizes are passed to backend without excessive frontend processing.
- **Overall Readiness**: The frontend architecture is clean and robust. To fully integrate the new Intelligent Document Processing engine, modifications are restricted solely to mapping the UI logic for 7/12 uploads in the Dashboard and Wizard components.

## 5. Conclusion
**Is the Frontend ready for integration? YES.**
The frontend requires targeted modifications in `ProfileWizard.tsx` and `Dashboard.tsx` to align the `doc_type` naming and process the newly added agricultural fields from the Gemini backend. No structural or architectural refactoring is needed.
