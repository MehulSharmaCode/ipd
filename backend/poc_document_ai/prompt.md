# Prompt Engineering — Maharashtra 7/12 Document Understanding

## Overview

This document explains the exact prompts sent to Gemini 2.5 Flash and the reasoning behind their design.

Two prompts are used:
1. **Analysis Prompt** — Preliminary document assessment (Phase 4)
2. **Extraction Prompt** — Structured field extraction (Phases 5–7)

---

## Design Philosophy

### NOT OCR — Document Understanding

The fundamental design decision is to **never ask Gemini to perform OCR**.

Traditional OCR reads every character left-to-right, top-to-bottom. Maharashtra 7/12 documents have:
- Mixed printed and handwritten Devanagari text
- Tabular layouts with merged cells
- Stamps, seals, and annotations
- Multiple writers with different handwriting styles

Instead, we instruct Gemini to **understand the document as a domain expert would** — extracting meaning, not characters.

### Role Priming

Both prompts begin by establishing Gemini's role:
- "You are an expert in Maharashtra land revenue records"
- "You are a senior document intelligence specialist"

This primes the model to leverage its training on Indian government document formats, Marathi language, and agricultural terminology.

### Null-Over-Hallucination Policy

Every prompt enforces:
```
If a field cannot be confidently determined, set it to null.
NEVER guess. NEVER hallucinate.
```

This is the most critical design decision. In a farmer profile system, wrong data is worse than missing data. A null field can be manually filled; a hallucinated survey number creates legal complications.

### Strict JSON Output

Prompts explicitly demand:
```
Return ONLY the JSON object. No markdown. No code fences. No explanation.
```

The client-side cleanup handles the occasional markdown fence that Gemini wraps around JSON, but the prompt minimizes this behavior.

---

## Prompt 1: Analysis Prompt (Phase 4)

### Purpose
Before extraction, assess whether the document is suitable for automated processing.

### Full Prompt

```
You are a senior document intelligence specialist with deep expertise in Indian
government land records, particularly Maharashtra revenue documents.

Analyze the uploaded document image and provide a structured assessment.
Return ONLY a valid JSON object — no markdown, no explanations, no surrounding text.

{
  "document_type": "<type of document>",
  "document_title": "<exact title printed on the document, in original script>",
  "languages_detected": ["<list of languages/scripts>"],
  "content_breakdown": {
    "printed_text_percentage": <estimated percentage>,
    "handwritten_text_percentage": <estimated percentage>,
    "tables_present": <true/false>,
    "stamps_or_seals_present": <true/false>
  },
  "image_quality": {
    "overall": "<excellent/good/fair/poor>",
    "issues": ["<list any issues>"]
  },
  "extraction_feasibility": {
    "overall": "<high/medium/low>",
    "confidently_extractable_fields": ["<list>"],
    "uncertain_fields": ["<list>"],
    "unreadable_fields": ["<list>"]
  },
  "observations": "<additional observations>"
}
```

### Why This Structure

| Field | Rationale |
|-------|-----------|
| `document_type` | Confirms Gemini correctly identifies 7/12 vs. other document types |
| `languages_detected` | Validates Gemini recognises Devanagari and any English sections |
| `content_breakdown` | Quantifies the handwriting challenge before extraction |
| `image_quality` | Early warning for poor scans that will produce low-quality extraction |
| `extraction_feasibility` | Pre-assessment lets us decide whether to even attempt extraction |
| `observations` | Captures edge cases the fixed schema doesn't cover |

---

## Prompt 2: Extraction Prompt (Phases 5–7)

### Purpose
Extract the specific fields needed for a Farmer Profile from the 7/12 document.

### Full Prompt

```
You are an expert in Maharashtra land revenue records, agricultural documentation,
and the Satbara Utara (गांव नमुना नं. ७/१२) system.

Your task is NOT to perform OCR or transcribe every word.

Your task is to UNDERSTAND the document and extract ONLY the structured information
required for building a Farmer Profile.

Study the document carefully. Maharashtra 7/12 documents follow a standard format:
- Top header: "गांव नमुना नं. ७, ७ अ व १२" (Village Form No. 7, 7A and 12)
- Left section: Survey/Gat number (भूमापन क्रमांक / गट नं.)
- Ownership section: Names of land holders (खातेदाराचे नाव)
- Area section: Land area in Hectare-Are format (हे.आर / क्षेत्र)
- Right section: Crop details, soil type, irrigation (पिकाखालील क्षेत्र)
- Bottom section: Mutation entries (फेरफार नोंदी)

Extract the following fields. Return ONLY a valid JSON object.

{
  "document_type": "7_12",
  "owner_name": "<primary land owner name>",
  "survey_number": "<survey number>",
  "gat_number": "<gat number>",
  "village": "<village name>",
  "taluka": "<taluka name>",
  "district": "<district name>",
  "land_area": "<total land area with unit>",
  "current_crop": "<primary crop(s)>",
  "irrigation": "<irrigation type>",
  "soil_type": "<soil type>",
  "ownership_type": "<ownership type>",
  "additional_info": {
    "co_owners": ["<list of co-owners>"],
    "mutation_entries": "<number>",
    "hissa_number": "<hissa number>",
    "pot_hissa": "<pot hissa>",
    "land_use": "<agricultural/non-agricultural>",
    "season": "<kharif/rabi/both>"
  }
}
```

### Why These Fields

| Field | Farmer Profile Use |
|-------|-------------------|
| `owner_name` | Primary identity for the profile |
| `survey_number` / `gat_number` | Unique land parcel identifier for verification |
| `village` / `taluka` / `district` | Geographic targeting for regional schemes |
| `land_area` | Eligibility for size-based schemes (marginal/small/medium farmer) |
| `current_crop` | Crop-specific subsidies and advisories |
| `irrigation` | Irrigation scheme eligibility |
| `soil_type` | Soil health card linkage |
| `ownership_type` | Joint/individual affects scheme eligibility |
| `additional_info` | Supplementary data for richer profiles |

### Key Engineering Choices

1. **Layout hints in the prompt**: Describing where each field typically appears (header, left section, right section) helps Gemini navigate the form structure.

2. **Marathi field labels**: Including both Marathi (भूमापन क्रमांक) and English translations helps Gemini map printed Devanagari headers to the JSON keys.

3. **Devanagari preference**: "Prefer Devanagari script for names and places" — since the document is in Marathi, preserving the original script reduces transliteration errors.

4. **String-typed numerics**: Survey numbers and areas are strings, not numbers, because they can contain hyphens, slashes, and units.

---

## Prompt Iteration Suggestions

For future improvement:
1. Add 2–3 few-shot examples of correct extractions from different document samples
2. Include a glossary of common Marathi agricultural terms
3. Provide a list of valid taluka/district names for the target region
4. Ask Gemini to return a confidence score (0.0–1.0) for each field
5. Consider a two-pass approach: structure extraction first, then detail extraction
