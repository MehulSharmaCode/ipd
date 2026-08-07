# Root Cause Analysis — End-to-End Testing Findings

**Project:** AgriSense — Intelligent Document Processing Frontend Integration
**Date:** 2026-08-06
**Scope:** Diagnosis only. No code modified.

---

## Summary of Issues Found

| # | Severity | Component | Issue |
|---|---|---|---|
| 1 | **Critical** | ProfileWizard → `mapExtractionToProfile` | Aadhaar `fields` key mismatch: frontend reads `full_name`, backend writes `full_name`; **works** — but gender value `"MALE"` won't match Select option `"Male"` |
| 2 | **Critical** | ProfileWizard → `mapExtractionToProfile` | The **confidence calculation** in `handleFileUpload` treats each field's `.confidence` value as if it is already 0–100; backend returns 0.0–1.0. Result: confidence always rounds to ~0%. **Non-blocking but misleading.** |
| 3 | **Critical** | ProfileWizard → onboarding flow | PAN fields (`full_name` from PAN) are silently dropped because the "only fill if currently blank" guard fires incorrectly after Aadhaar already set `full_name`. But PAN does return `full_name` too — this is by design and acceptable. The real gap: **`age` is never mapped from Aadhaar `dob` field**. |
| 4 | **Critical** | `mapExtractionToProfile` | `gender` from Aadhaar: OCR parser emits `"MALE"` / `"FEMALE"` (uppercase). The `<Select>` options are `"Male"` / `"Female"` (title-case). The value written to state won't match any `<SelectItem value>`. Result: dropdown shows blank even though state is populated. |
| 5 | **High** | 7/12 extraction → Farm Details | `season` field is nested inside `additional_info` in Gemini's JSON (see `gemini_pipeline.py` line 133). `mapExtractionToProfile` reads `fields['season']` correctly — **however** the crop season `<Select>` options are `"Kharif"` / `"Rabi"` / `"Zaid"`. Gemini returns Marathi/English free text (e.g. `"Kharif"`, `"kharif"`, `"खरीप"`). Case and language mismatch silently prevents the dropdown from populating. |
| 6 | **High** | 7/12 extraction → Farm Details | `irrigation` field: Gemini returns free text (e.g. `"Well irrigation"`, `"Canal"`, `"Rain-fed"`). Frontend `<Select>` options are `"Well"` / `"Canal"` / `"Rain"` / `"River"` / `"Borewell"`. Partial-match mismatch — value is written to state but does not equal any `<SelectItem value`, so dropdown appears blank. |
| 7 | **High** | 7/12 extraction → Farm Details | `soil_type` from Gemini returns free text (e.g. `"Black cotton soil"`, `"Red soil"`). Frontend options are `"Black"` / `"Red"`. Written to state but never matches a `<SelectItem>`. |
| 8 | **Medium** | `mapExtractionToProfile` — Aadhaar | `dob` and `birth_year` are extracted and set by the backend but never read by `mapExtractionToProfile`. `age` is therefore never derived or pre-filled. |
| 9 | **Medium** | Validation asymmetry | **PAN uploaded as Aadhaar → rejected ✓.** **Aadhaar uploaded as PAN → accepted ✗.** Root cause detailed below (Task 5). |
| 10 | **Low** | Wizard flow architecture | Current order (Aadhaar → PAN → 7/12 → Personal → Farm) vs proposed alternative. Analysis in Task 4. |

---

## Task 1 — Aadhaar Upload Execution Trace

### Complete call chain

```
handleFileUpload(e, 'aadhar')          ProfileWizard.tsx:305
  ↓ DOC_TYPE_MAP['aadhar'] = 'aadhar'  ProfileWizard.tsx:64
  ↓ POST /upload/  (multipart)          ProfileWizard.tsx:329
        ↓
    upload.py:107 → document_router.route(file_path, 'aadhar')
        ↓
    AadhaarProcessor.process()          ocr/aadhaar.py:32
        ↓
    run_ocr_pipeline(file_path, 'aadhar')  pipeline.py:89
        ↓
    Stage 4: parser.extract(text)       → fields = {
                                             "aadhaarNumber": "XXXX XXXX XXXX",
                                             "name": "MEHUL SHARMA",
                                             "dob": "01/01/1990",
                                             "gender": "MALE"
                                           }
        ↓
    aadhaar.py:53-62 → result.set_field(...)
        result.fields = {
            "aadhar_number": ExtractedField(value="...", confidence=0.94),
            "full_name":     ExtractedField(value="MEHUL SHARMA", confidence=0.94),
            "dob":           ExtractedField(value="01/01/1990", confidence=0.94),
            "birth_year":    ExtractedField(value="1990", confidence=0.94),
            "gender":        ExtractedField(value="MALE", confidence=0.94),
        }
        ↓
    upload.py:152 → response["fields"] = result_dict["fields"]
        = {
            "aadhar_number": { "value": "...", "source_document": "aadhar", "confidence": 0.94 },
            "full_name":     { "value": "MEHUL SHARMA", "source_document": "aadhar", "confidence": 0.94 },
            "dob":           { "value": "01/01/1990", ... },
            "gender":        { "value": "MALE", ... },
          }
```

**Frontend receives:** `data.fields` is the above object — ExtractedField dicts.

```
handleFileUpload cont.
  ↓ data.fields = { aadhar_number: {value,…}, full_name: {value,…}, gender: {value,…}, dob: {value,…} }
  ↓ mapExtractionToProfile('aadhar', 'aadhar', fields, isValid)
        ↓
        fieldValue(fields, 'full_name')   → "MEHUL SHARMA"  ✓ (key matches)
        fieldValue(fields, 'gender')      → "MALE"          ✓ (key matches)
        fieldValue(fields, 'aadhar_number') → "..."         ✓ (key matches)
        NOTE: fieldValue(fields, 'dob') is NEVER called     ✗ BUG #8
        NOTE: fieldValue(fields, 'birth_year') is NEVER called ✗ BUG #8
  ↓ profileUpdates = {
        full_name: "MEHUL SHARMA",
        gender: "MALE",           ← uppercase — BUG #4
        aadhar_number: "...",
        is_aadhar_verified: true,
    }
  ↓ setProfile(prev → next)
        k='full_name': prev.full_name == '' → written ✓
        k='gender': prev.gender == '' → written — but value is "MALE" not "Male" ✗ BUG #4
```

### Where it stops propagating

**`full_name`:** Written to state correctly as `"MEHUL SHARMA"`. The `<Input>` is bound to `profile.full_name` — **this should render correctly**. If the user reports it is NOT rendering, that points to a Step 2 mounting issue where the component re-reads the initial empty profile after navigation.

**`gender`:** Written to state as `"MALE"`. The `<Select>` has `<SelectItem value="Male">`. These do not match → dropdown appears blank. **Root cause: case mismatch.**

**`age`:** Never written. `dob` is extracted but `mapExtractionToProfile` does not read it and does not derive age. **Root cause: missing field in mapper.**

---

## Task 2 — PAN Upload Execution Trace

```
handleFileUpload(e, 'pan')
  ↓ DOC_TYPE_MAP['pan'] = 'pan'
  ↓ POST /upload/
        ↓
    PANProcessor.process()             ocr/pan.py:32
        ↓
    Stage 4: parser.extract(text) → fields = {
                                       "panNumber": "ABCDE1234F",
                                       "name": "MEHUL SHARMA",
                                       "dob": "01/01/1990",
                                     }
        ↓
    pan.py:53-60 → result.fields = {
        "pan_number": ExtractedField(value="ABCDE1234F", ...),
        "full_name":  ExtractedField(value="MEHUL SHARMA", ...),
        "dob":        ExtractedField(value="01/01/1990", ...),
    }
```

**Frontend receives:** `data.fields` with `pan_number`, `full_name`, `dob`.

```
mapExtractionToProfile('pan', 'pan', fields, isValid)
  ↓
  backendDocType === 'pan' branch
  ↓ only reads 'pan_number' field (line 141–145)
  ↓ profileUpdates = { pan_number: "ABCDE1234F", is_pan_verified: true }
```

### BUG: `full_name` from PAN is silently discarded

**File:** `ProfileWizard.tsx`, `mapExtractionToProfile()`, line 140–145

The `pan` branch only maps `pan_number`. The `full_name` and `dob` fields returned by the PAN processor are **never read**. While the "don't overwrite Aadhaar name" principle is sound, the implementation simply ignores them entirely rather than mapping them conditionally.

**Impact:** If a user skips Aadhaar upload (or Aadhaar OCR fails), PAN cannot provide the name fallback.

---

## Task 3 — 7/12 Extraction: Why Only 2 of 5 Fields Populate

### Issue A: `season` key location mismatch

**Backend:** `gemini_pipeline.py` line 133:
```python
if additional.get("season"):
    result.set_field("season", additional["season"], confidence=0.80)
```
`season` is stored under `result.fields["season"]` — key is `"season"`.

**Frontend:** `mapExtractionToProfile` line 172:
```javascript
const season = fieldValue(fields, 'season');
```
This reads `fields["season"]` — key matches ✓. **Not a key mismatch.**

**Root cause for season not filling the dropdown:** The Gemini model returns a free-text string such as `"Kharif"`, `"kharif"`, `"Rabi season"`, or `"खरीप"`. The `<SelectItem>` values are exactly `"Kharif"`, `"Rabi"`, `"Zaid"`. A React `<Select>` controlled component only renders the selected option if `value` equals one of the `<SelectItem value>` props **exactly**. The state IS updated, but the dropdown appears blank because the string doesn't match.

### Issue B: `irrigation` / `soil_type` free-text vs. enum mismatch (BUG #6, #7)

**Backend Gemini extraction returns (examples):**
- `"irrigation": "Well irrigation"` / `"Canal irrigation"` / `"Rainfed"`
- `"soil_type": "Black cotton soil"` / `"Black soil"` / `"Red laterite"`

**Frontend `<SelectItem>` values (exact strings required):**
- irrigation: `"Well"`, `"Canal"`, `"Rain"`, `"River"`, `"Borewell"`
- soil_type: `"Alluvial"`, `"Black"`, `"Red"`, `"Laterite"`, `"Desert"`, `"Mountain"`

**What happens:** The raw Gemini string is written to state (e.g. `irrigation_type = "Well irrigation"`), but the `<Select>` control will only show a value if it exactly matches a `<SelectItem value>`. There is no normalization step. The input is silently bound to state but never matches any option → dropdown appears blank.

**This is why the UI shows "AI Extracted" badges but the dropdowns appear empty.** The badge appears because `aiFilledFields` contains the field key (added whenever Gemini returns a non-null value). The state contains the raw Gemini string. The Select component cannot find a matching option.

### Issue C: `land_area` numeric parsing

`land_area` from Gemini may be `"2.5 Hectare"` or `"250 Are"` or `"2 acres"`. The regex `replace(/[^\d.]/g, '')` extracts the numeric portion. This is correct for hectares but wrong for "Are" (1 hectare = 100 Are). No unit detection exists.

---

## Task 4 — Onboarding Flow Architecture

### Current flow
```
Step 1: Aadhaar + PAN Upload (identity)
Step 2: Personal Details
Step 3: 7/12 Land Record (optional)
Step 4: Farm Details Review
Step 5: Success
```

### Proposed alternative
```
Step 1: Aadhaar Upload
Step 2: PAN Upload
Step 3: 7/12 Land Record
Step 4: Personal Details
Step 5: Farm Details
Step 6: Success
```

### Recommendation: **Keep the current architecture (Steps 1–5)**

**Reason 1 — Information completeness at review time.**
When the user reaches Personal Details (Step 2), they have already verified both Aadhaar and PAN. They can see their pre-filled name, Aadhaar number, and PAN number simultaneously and confirm or correct them in one screen. Splitting Aadhaar and PAN into separate steps creates unnecessary round trips for a task the user understands as a single "identity verification" action.

**Reason 2 — Progressive enhancement principle.**
Aadhaar and PAN are identity documents that share the same review concern (name, DOB, ID number). They belong in the same step. The 7/12 is a different domain (agricultural) and correctly occupies its own step.

**Reason 3 — Fewer mandatory steps.**
The proposed 6-step flow adds one mandatory step (splitting Aadhaar and PAN). The current 5-step flow is already at the upper limit of what UX research shows users will complete without dropout.

**Reason 4 — Step 3 (Personal Details) must remain before 7/12.**
The user must set their `state` field before the 7/12 step, because the district auto-fill from 7/12 should only apply when the district field is blank, and the state is needed for scheme matching context. Having Personal Details before the 7/12 step preserves this ordering.

**Verdict: current 5-step architecture is correct. Do not change it.**

---

## Task 5 — Asymmetric Document Validation

### Observation
- PAN uploaded as Aadhaar → **rejected** ✓
- Aadhaar uploaded as PAN → **accepted** ✗

### Execution trace

**Case 1: PAN uploaded as Aadhaar**

```
upload.py:107 → document_router.route(file_path, 'aadhar')
  ↓
AadhaarProcessor.process()
  ↓
run_ocr_pipeline(file_path, expected_doc_type='aadhar')
  ↓
classification.classify(ocr_text)
  → PAN card keywords hit: "INCOME TAX", "PERMANENT", etc.
  → classified as 'PAN' (not 'AADHAAR_FRONT')
  ↓
pipeline.py:137–150 — mismatch detection:
  hint_is_aadhaar = True   (user said 'aadhar')
  actual_is_aadhaar = False (classified as 'PAN')
  → logs warning ✓
  ↓
validate_fields('PAN', extracted_fields)
  → 'panNumber' present, passes PAN validation
  → validation.valid = True  ← PROBLEM
  ↓
aadhaar.py:53–62 — maps result.fields:
  fields.get("aadhaarNumber") → None (PAN card has no Aadhaar number)
  fields.get("name") → present
  → result.fields has NO "aadhar_number"
  ↓
aadhaar.py:65–68 → result.validation = ocr_result.validation
  BUT ocr_result.validation.valid was set by validate_aadhaar_fields()
  which CHECKS: "aadhaarNumber" in fields → False → adds warning "Aadhaar number could not be extracted."
  → valid=False, warnings=["Aadhaar number could not be extracted."]
  → CORRECTLY REJECTED ✓
```

**Why PAN-as-Aadhaar is rejected:**
`validate_aadhaar_fields()` (validation.py line 101–106) requires `aadhaarNumber` in the OCR-extracted `fields` dict. A PAN card has no 12-digit Aadhaar-format number → `aadhaarNumber` is absent → validation fails → `valid=False`.

---

**Case 2: Aadhaar uploaded as PAN**

```
upload.py:107 → document_router.route(file_path, 'pan')
  ↓
PANProcessor.process()
  ↓
run_ocr_pipeline(file_path, expected_doc_type='pan')
  ↓
classification.classify(ocr_text)
  → Aadhaar card text: "GOVERNMENT OF INDIA", "DOB", "MALE", 12-digit number
  → Aadhaar keywords hit ≥ 2: classified as 'AADHAAR_FRONT'
  ↓
pipeline.py:137–150 — mismatch detection:
  hint_is_pan = True   (user said 'pan')
  actual_is_pan = False (classified as 'AADHAAR_FRONT')
  → logs WARNING but DOES NOT REJECT — pipeline continues ← ROOT CAUSE
  ↓
parser = get_parser('AADHAAR_FRONT')
→ Aadhaar parser runs on the Aadhaar card
→ extracts: name, aadhaarNumber, dob, gender (all valid)
  ↓
validate_fields('AADHAAR_FRONT', fields)
  → "aadhaarNumber" present → validate_aadhaar_number() → PASSES
  → validation.valid = True
  ↓
pan.py:52–60 — maps result.fields:
  fields.get("panNumber") → None  (no PAN number on Aadhaar card)
    → pan_number NOT set in result.fields
  fields.get("name") → present → sets full_name
  ↓
pan.py:63–68 → result.validation = ocr_result.validation
  BUT ocr_result.validation was set by validate_aadhaar_fields()
  which PASSED (aadhaarNumber was found on the card)
  → valid = True  ← ACCEPTS AADHAAR AS PAN ✗
```

### Root cause of asymmetry

**File:** `backend/app/ml/ocr/pipeline.py`, lines 136–150

The mismatch detection block **only logs a warning**. It does not return an error result. Processing continues with whatever the classifier determined.

**File:** `backend/app/ml/ocr/pipeline.py`, line 179–181

`validate_fields()` is called with the **classifier's determined type** (`'AADHAAR_FRONT'`), not the **user's requested type** (`'pan'`). When Aadhaar is uploaded as PAN:
- The classifier correctly identifies it as `AADHAAR_FRONT`
- `validate_aadhaar_fields()` runs and passes (because it is a valid Aadhaar card)
- The PANProcessor copies this `valid=True` into its result
- The upload API accepts it

**File:** `backend/app/document_processing/ocr/pan.py`, lines 63–68

The PANProcessor overwrites its own `result.validation` with `ocr_result.validation` (line 63–66). It does not verify that the OCR pipeline validated a PAN document — it blindly inherits the validation result of whatever type was classified.

**Additional asymmetry cause:** `validate_pan_fields()` (validation.py line 125–150) requires `panNumber` in the fields dict. When a PAN card is processed as Aadhaar, the Aadhaar parser runs → no `panNumber` extracted → `validate_pan_fields` would fail. But because the classifier determined `AADHAAR_FRONT`, `validate_aadhaar_fields()` is called instead (which passes). The PAN validator never runs.

---

## Consolidated Issue Table (for implementation)

| # | File | Function | Line | Issue | Recommended Fix |
|---|---|---|---|---|---|
| 1 | `ProfileWizard.tsx` | `mapExtractionToProfile` | ~132 | `gender` stored as `"MALE"` but Select needs `"Male"` | Normalize: `value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()` |
| 2 | `ProfileWizard.tsx` | `mapExtractionToProfile` | ~125–139 | `dob` and `birth_year` fields never read; `age` never derived | Parse `birth_year` → `new Date().getFullYear() - birthYear` to pre-fill age |
| 3 | `ProfileWizard.tsx` | `mapExtractionToProfile` | ~140–145 | PAN `full_name` silently discarded; cannot act as fallback | Map `full_name` from PAN if currently blank (same guard as Aadhaar) |
| 4 | `ProfileWizard.tsx` | `mapExtractionToProfile` | ~160–188 | `irrigation`, `soil_type`, `season`, `ownership_type` written as Gemini free-text; Select dropdowns need exact enum values | Add normalization table: map common Gemini phrases to enum values before writing to state |
| 5 | `ProfileWizard.tsx` | `handleFileUpload` | ~334–342 | Confidence calculated as `sum(confidence * 100)` — but `confidence` is already 0.0–1.0; result ~1% | Remove `* 100` multiplier |
| 6 | `pipeline.py` | `process()` | ~136–150 | Mismatch detection only logs; does not reject | Return error result when classifier-type and user-hint type are incompatible classes |
| 7 | `pan.py` + `aadhaar.py` | `process()` | ~63–68 | Processors inherit the classifier's validation result regardless of whether the classified type matches the requested type | Validate against `doc_type` parameter, not classifier output |

---

## Files Requiring Change (implementation phase)

**Frontend (no backend changes for issues #1–5):**
- `frontend/src/pages/ProfileWizard.tsx` — fix `mapExtractionToProfile()` and confidence calculation

**Backend (for issues #6–7 — asymmetric validation):**
- `backend/app/ml/ocr/pipeline.py` — enforce mismatch rejection
- `backend/app/document_processing/ocr/pan.py` — validate against requested doc_type
- `backend/app/document_processing/ocr/aadhaar.py` — validate against requested doc_type

---

> **Diagnosis complete. No code modified.**
