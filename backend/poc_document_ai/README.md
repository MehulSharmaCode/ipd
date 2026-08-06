# Gemini 2.5 Flash — Document Understanding PoC

## Purpose

This is a **completely isolated Proof of Concept** to validate whether Google Gemini 2.5 Flash can reliably understand and extract structured agricultural data from handwritten Maharashtra 7/12 (Satbara Utara) land revenue documents.

> ⚠️ **This module is NOT integrated into the main application.**  
> Nothing in `app/` depends on or imports from `poc_document_ai/`.  
> This PoC must prove successful before any production integration is attempted.

---

## Architecture

```
backend/
├── .env                          # Contains GEMINI_API_KEY
├── samples/
│   └── satbara/
│       └── satbara1.jpeg         # Sample 7/12 document(s)
├── poc_document_ai/              # ← This module (isolated)
│   ├── __init__.py
│   ├── connectivity_test.py      # Phase 2: Verify API connectivity
│   ├── gemini_client.py          # Gemini SDK wrapper
│   ├── prompt.py                 # Engineered prompts (analysis + extraction)
│   ├── validator.py              # JSON schema validation
│   ├── run_poc.py                # Main runner (all phases)
│   ├── prompt.md                 # Prompt engineering documentation
│   ├── README.md                 # This file
│   ├── sample_output.json        # Generated: latest extraction result
│   └── analysis_report.md        # Generated: full evaluation report
└── app/                          # ← Main application (UNTOUCHED)
```

---

## Prerequisites

### 1. API Key

Add your Google AI Studio API key to `backend/.env`:

```
GEMINI_API_KEY=your_api_key_here
```

Get a key from: https://aistudio.google.com/apikey

### 2. Install Dependencies

```bash
cd backend
source .venv/bin/activate
pip install google-genai
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 3. Sample Documents

Place 7/12 document images (`.jpg`, `.jpeg`, `.png`) in:

```
backend/samples/satbara/
```

---

## How to Run

### Step 1: Connectivity Test (Recommended)

Verify Gemini is reachable before running the full PoC:

```bash
cd backend
source .venv/bin/activate
python -m poc_document_ai.connectivity_test
```

Expected output:
```
✓ GEMINI_API_KEY loaded (54 chars, ending …_TA)
✓ google-genai SDK imported successfully
✓ Gemini client created
✓ Gemini Connected Successfully
```

### Step 2: Full PoC

Run the complete document understanding pipeline:

```bash
python -m poc_document_ai.run_poc
```

This will:
1. Test connectivity (Phase 2)
2. Discover all samples in `samples/satbara/`
3. For each sample:
   - Run document analysis (Phase 4)
   - Run structured extraction (Phases 5–7)
   - Validate the output (Phase 8)
4. Print results to terminal (Phase 9)
5. Generate report files (Phase 10)

---

## Expected Outputs

### Terminal Output

For each sample, you'll see:
- Document analysis results (type, languages, quality, feasibility)
- Extracted JSON with all fields
- Validation summary (pass/fail, extraction rate, missing fields)
- Execution timing

### Generated Files

| File | Description |
|------|-------------|
| `sample_output.json` | The latest successful JSON extraction |
| `analysis_report.md` | Full evaluation report with strengths, weaknesses, and recommendations |

---

## What This PoC Tests

| Question | How We Test It |
|----------|---------------|
| Can Gemini read Devanagari handwriting? | Extract owner names, village, taluka |
| Can Gemini understand document layout? | Extract tabular data (survey numbers, area) |
| Is the JSON output reliable? | Validate schema, types, and completeness |
| Is extraction fast enough? | Measure per-document timing |
| Are results accurate? | Compare against visually verified values |

---

## Model Details

- **Model:** `gemini-2.5-flash`
- **SDK:** `google-genai` (official Google Gen AI SDK)
- **API calls per document:** 2 (analysis + extraction)
- **Estimated cost:** ~$0.002–$0.005 per document

---

## Status

**Current status: PoC only — NOT integrated into the application**

Next steps (after successful PoC):
1. Add `SatbaraParser` to the existing parser registry
2. Route 7/12 documents through Gemini instead of Tesseract
3. Add confidence scoring and human-in-the-loop review
4. Integrate with the FastAPI upload endpoint
