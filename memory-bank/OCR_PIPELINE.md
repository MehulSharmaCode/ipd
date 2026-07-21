# OCR_PIPELINE.md — AgriSense OCR System
> **Last Updated:** 2026-07-21 | Cross-reference: ARCHITECTURE.md, API_REFERENCE.md

---

## Overview

The OCR pipeline processes uploaded Aadhaar and PAN card images to extract structured identity information. It operates as a **7-stage pipeline** that is the sole entry point for document processing — no other module calls Tesseract directly.

**Key Design Principles:**
1. Each stage is independently testable
2. `pipeline.py` is the ONLY orchestrator — upload API calls only `process()`
3. OCR failure is non-fatal — upload always succeeds; OCR data is best-effort
4. Confidence score blends OCR confidence (60%) + classification confidence (40%)

---

## Pipeline Stages

```
Stage 1: File Validation
Stage 2: OCR Text Extraction  ← Tesseract
Stage 3: Document Classification
Stage 4: Field Extraction (Parsing)
Stage 5: Field Validation
Stage 6: Profile Mapping
Stage 7: Response Construction
```

### Stage 1: File Validation
**File:** `app/ml/ocr/pipeline.py`

Checks:
- File exists on disk
- Extension in `{.pdf, .jpg, .jpeg, .png}`

Fails with: `OCRPipelineResult(documentType="UNKNOWN", confidence=0.0, error="...")`

---

### Stage 2: OCR Text Extraction
**Files:** `app/ml/ocr/ocr_service.py`, `app/ml/ocr/preprocessing.py`, `app/ml/ocr/config.py`

#### Tesseract Auto-Detection (`config.py`)
Detection runs at **module import time** (singleton). Priority:
1. `TESSERACT_PATH` environment variable
2. `shutil.which("tesseract")` — searches augmented PATH (adds Homebrew dirs)
3. Known platform defaults:
   - macOS: `/opt/homebrew/bin/tesseract`, `/usr/local/bin/tesseract`
   - Linux: `/usr/bin/tesseract`, `/usr/local/bin/tesseract`
   - Windows: `C:\Program Files\Tesseract-OCR\tesseract.exe`
4. Fail with diagnostic error

Also auto-detects `TESSDATA_PREFIX` for language data.

#### Image Preprocessing (`preprocessing.py`)
Full preprocessing pipeline (returns binary numpy array for Tesseract):
```
Input (file path or numpy array)
  │
  ▼ Load to BGR numpy array (cv2.imread)
  ▼ Resolution enhancement: upscale to ≥1000×600 if smaller (INTER_CUBIC)
  ▼ Grayscale conversion (cv2.COLOR_BGR2GRAY)
  ▼ Deskew: Canny edges → HoughLinesP → median angle → warpAffine (correct if 0.5°–45°)
  ▼ Bilateral filter: d=9, sigmaColor=75, sigmaSpace=75 (noise removal, edge-preserving)
  ▼ Adaptive threshold: GAUSSIAN_C, THRESH_BINARY, blockSize=11, C=2 (handle uneven lighting)
  ▼ Morphological opening: 1×1 kernel (remove salt-pepper noise)
  ▼ Border padding: 10px white border (prevent Tesseract edge misread)
  │
  ▼ Binary numpy array (ready for Tesseract)
```

For PDF files:
```
PyMuPDF open PDF
  → load each page
  → render at 3× scale (Matrix(3.0, 3.0)) for high resolution
  → convert Pixmap to numpy (RGB → BGR)
  → standard preprocess (skip resolution enhancement — already high-res)
  → concatenate all page texts
```

#### Tesseract Configuration
```
--oem 3   # Both legacy + LSTM engines (most accurate)
--psm 6   # Uniform block of text (best for ID cards)
```

Returns:
- `OCRResult.text`: full string
- `OCRResult.confidence`: average of word-level confidences (0–100)
- `OCRResult.processing_time_ms`: elapsed time

---

### Stage 3: Document Classification
**File:** `app/ml/ocr/classification.py`

**Method:** Rule-based keyword matching on extracted text.

```python
ClassificationResult:
  document_type: "AADHAAR_FRONT" | "AADHAAR_BACK" | "PAN" | "UNKNOWN"
  confidence: float (0.0–1.0)
```

Classification logic (approximate):
- Looks for: "UIDAI", "Aadhaar", "Unique Identification", "Date of Birth", "DOB" → AADHAAR_FRONT
- Looks for: address keywords, "S/o", "W/o" → AADHAAR_BACK
- Looks for: "Income Tax", "Permanent Account Number", "PAN" → PAN
- If no strong signal → UNKNOWN

**On UNKNOWN:** Pipeline returns early with a user-friendly warning.

**Mismatch detection:** If user uploaded as "aadhar" but classified as "PAN", a warning is logged (pipeline continues — not blocked).

---

### Stage 4: Field Extraction (Parsing)
**File:** `app/ml/ocr/parsers.py`

#### AadhaarParser
Used for both AADHAAR_FRONT and AADHAAR_BACK.

```python
Extracted fields:
  aadhaarNumber: "DDDD DDDD DDDD"  (12 digits, formatted with spaces)
  dob: "DD/MM/YYYY"
  birthYear: "YYYY"
  gender: "Male" | "Female" | "Transgender"
  name: "First Last" (heuristic extraction)
```

Regex patterns:
```python
_AADHAAR_RE = r"\b(\d{4})[\s\-]*(\d{4})[\s\-]*(\d{4})\b"
_DOB_FULL_RE = r"\b(\d{2})[/\-](\d{2})[/\-](\d{4})\b"
_DOB_YEAR_RE = r"\b(19|20)\d{2}\b"
_GENDER_RE = r"\b(MALE|FEMALE|TRANSGENDER)\b"
```

Name extraction heuristic:
- Lines with 2–5 words, each starting uppercase
- No digits in line
- Line length < 50 chars
- Not containing known skip keywords (GOVERNMENT, INDIA, UIDAI, AADHAAR, etc.)

#### PANParser
```python
Extracted fields:
  panNumber: "AAAAA9999A"
  dob: "DD/MM/YYYY"
  name: "First Last"
  fatherName: "Father Full Name"
```

Regex patterns:
```python
_PAN_RE = r"\b([A-Z]{5}[0-9]{4}[A-Z])\b"
_DOB_RE = r"\b(\d{2})[/\-](\d{2})[/\-](\d{4})\b"
```

Name/fatherName: First two heuristic name-like lines (title-case, 2–5 words, no digits).

#### OCR Character Fixes
```python
"|" → "I"
"l" → "I"  (lowercase L to uppercase I)
"\u2019" → "'"  (curly apostrophe)
```

#### Parser Registry
```python
PARSER_REGISTRY = {
    "AADHAAR_FRONT": AadhaarParser,
    "AADHAAR_BACK": AadhaarParser,
    "PAN": PANParser,
}
```

To add a new document type: implement `class XxxParser` with `extract(text: str) -> dict`, register in `PARSER_REGISTRY`.

---

### Stage 5: Field Validation
**File:** `app/ml/ocr/validation.py`

```python
ValidationResult:
  valid: bool
  warnings: list[str]
```

#### Aadhaar Validators
| Field | Rule |
|---|---|
| `aadhaarNumber` | Exactly 12 digits, first digit ≠ 0 or 1 (UIDAI spec) |
| `name` | Length ≥ 2, no digits, ≤ 100 chars |
| `dob` | Format DD/MM/YYYY, day 1–31, month 1–12, year 1900–2024 |

Missing `aadhaarNumber` → adds warning "Aadhaar number could not be extracted."

#### PAN Validators
| Field | Rule |
|---|---|
| `panNumber` | Regex `^[A-Z]{5}[0-9]{4}[A-Z]$` |
| `name` | Same as above |
| `dob` | Same as above |

Missing `panNumber` → adds warning "PAN number could not be extracted."

---

### Stage 6: Profile Mapping
**File:** `app/ml/ocr/mapping.py`

Maps OCR fields to FarmerProfile field suggestions (for frontend auto-fill):

#### Aadhaar → Profile
| OCR Field | Profile Suggestion Key |
|---|---|
| `name` | `full_name_ocr_suggestion` |
| `aadhaarNumber` | `aadhar_number` |
| `gender` (normalized) | `gender` |
| `birthYear` (→ age calc) | `age` (2025 - birthYear) |
| `dob` | `dob` |

Gender normalization: MALE → "Male", FEMALE → "Female", TRANSGENDER → "Other"

#### PAN → Profile
| OCR Field | Profile Suggestion Key |
|---|---|
| `name` | `full_name_ocr_suggestion` |
| `panNumber` | `pan_number` |
| `dob` | `dob` |

**Security Note:** Aadhaar number is logged with last 4 digits only. PAN is logged with first 5 chars (non-sensitive alphabetic part).

---

### Stage 7: Response Construction
**File:** `app/ml/ocr/pipeline.py`

```python
OCRPipelineResult:
  documentType: str       # "AADHAAR_FRONT" | "AADHAAR_BACK" | "PAN" | "UNKNOWN"
  confidence: float       # 0–100 (blended: OCR confidence × 0.6 + class confidence × 100 × 0.4)
  fields: dict            # raw parsed fields
  validation: dict        # {"valid": bool, "warnings": list}
  profileSuggestions: dict # auto-fill suggestions for frontend
  rawTextSnippet: str     # first 300 chars of OCR text (debug only, NOT sent to frontend)
  processingTimeMs: float # end-to-end time in milliseconds
  error: str | None       # set on pipeline failure
```

**Confidence blending formula:**
```
blended_confidence = (ocr_confidence × 0.6) + (classification_confidence × 100 × 0.4)
```

---

## Database Update (Post-OCR)

After pipeline completes, `upload.py` updates the farmer record:
```python
# Always: record document path
{"$addToSet": {"documents_uploaded": "aadhar:uploads/filename.jpg"}}

# Only if validation.valid == True:
{"$set": {"aadhar_number": "...", "is_aadhar_verified": True}}
# or
{"$set": {"pan_number": "...", "is_pan_verified": True}}
```

DB update failure is **non-fatal** — OCR results are still returned.

---

## Tesseract Health Check

**Endpoint:** `GET /api/monitoring/ocr-health`
**Script:** `backend/scripts/verify_ocr.py`

Returns full diagnostic: path, version, tessdata, platform info.

---

## Supported File Types

| Extension | Method |
|---|---|
| `.pdf` | PyMuPDF → page render at 3× → preprocess |
| `.jpg`, `.jpeg`, `.png`, `.webp` | cv2.imread → preprocess |

Max file size: **10MB** (enforced in upload.py before OCR).

---

## Supported Document Types

| Type | Document |
|---|---|
| `AADHAAR_FRONT` | Aadhaar card front (name, DOB, gender, number) |
| `AADHAAR_BACK` | Aadhaar card back (address — parsed with same parser) |
| `PAN` | PAN card (name, father name, DOB, PAN number) |

---

## Known Limitations

1. **English text only** — Tesseract is configured for English. Hindi/regional language text on Aadhaar cards will not be parsed.
2. **No ML-based classification** — `document_classifier.pt` (PyTorch) is in the models directory but the active pipeline uses rule-based keyword classification.
3. **Heuristic name extraction** — names with unusual formatting (all-caps, non-standard spacing) may not be extracted.
4. **Low-quality images** — very blurry or poorly lit images produce low confidence and may not extract any fields.
5. **OCR character confusion** — "0" vs "O", "|" vs "I" corrections are applied selectively.
6. **Age calculation uses hardcoded 2025** — should use `datetime.now().year`.
7. **`ocr_engine.py` and `ocr_engine_v2.py` are legacy** — they have Windows-specific hardcoded Tesseract paths. The active service is `ocr_service.py`.

---

## Future Extensibility

To add a new document type (e.g., Land Records, Bank Passbook):
1. Create `XxxParser` class in `parsers.py` with `extract(text: str) -> dict`
2. Add `"DOCUMENT_TYPE": XxxParser` to `PARSER_REGISTRY`
3. Create `validate_xxx_fields()` in `validation.py`
4. Add `"DOCUMENT_TYPE": validate_xxx_fields` to `_VALIDATORS`
5. Create `map_xxx_to_profile()` in `mapping.py`
6. Add `"DOCUMENT_TYPE": map_xxx_to_profile` to `_MAPPERS`
7. Update classification keywords in `classification.py`
8. No changes needed to `pipeline.py` — it routes via registries

To replace regex PolicyIngestor with an LLM:
- Replace `app/ml/policy_engine/policy_ingestor.py:extract_rules()`
- Add LLM API call (Gemini/GPT) with structured output prompt
- Keep the same public interface: `extract_rules(text: str) -> dict`
