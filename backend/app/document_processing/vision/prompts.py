# backend/app/document_processing/vision/prompts.py
"""
Gemini Extraction Prompts
===========================
Production prompts for Maharashtra 7/12 document understanding.

Ported directly from the validated PoC (poc_document_ai/prompt.py).
These prompts achieved ~85% extraction accuracy on handwritten Marathi
7/12 documents during validation.

DO NOT modify these prompts without re-running the PoC validation.
"""

EXTRACTION_PROMPT = """You are an expert in Maharashtra land revenue records, agricultural documentation, and the Satbara Utara (गांव नमुना नं. ७/१२) system.

Your task is NOT to perform OCR or transcribe every word.

Your task is to UNDERSTAND the uploaded document and extract ONLY the structured information required for building a Farmer Profile.

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
  "owner_name": "<primary land owner name, in Devanagari as written, or transliterated to Latin script if clearly readable>",
  "survey_number": "<survey number / भूमापन क्रमांक, as string>",
  "gat_number": "<gat number / गट नंबर, as string, null if same as survey number or not present>",
  "village": "<village name / गाव>",
  "taluka": "<taluka name / तालुका>",
  "district": "<district name / जिल्हा>",
  "land_area": "<total land area with unit, e.g. '1.64 hectare' or '0.23 Are'>",
  "current_crop": "<primary crop(s) currently on the land, if mentioned>",
  "irrigation": "<irrigation type. Must be one of: Well, Canal, Rain, River, Borewell, or null if not mentioned>",
  "soil_type": "<soil type. Must be one of: Alluvial, Black, Red, Laterite, Desert, Mountain, or null if not present>",
  "ownership_type": "<land ownership type. Must be one of: Owned, Leased, Shared, or null if uncertain>",
  "additional_info": {
    "co_owners": ["<list of co-owner names if multiple owners are listed>"],
    "mutation_entries": "<number of mutation entries visible, or null>",
    "hissa_number": "<hissa/sub-division number if present, null otherwise>",
    "pot_hissa": "<pot hissa details if present, null otherwise>",
    "land_use": "<agricultural/non-agricultural/mixed, based on document>",
    "season": "<crop season. Must be one of: Kharif, Rabi, Zaid, or null if not visible>"
  }
}

CRITICAL RULES:
1. Return ONLY the JSON object. No markdown. No code fences. No explanation before or after.
2. If a field cannot be confidently determined from the document, set it to null.
3. NEVER guess. NEVER hallucinate. If uncertain, return null.
4. Prefer Devanagari script for names and places if that is how they appear in the document.
5. For numeric fields (survey number, area), extract the exact values as strings.
6. The JSON must be valid and parseable by any standard JSON parser.
7. Do not add any fields beyond what is specified in the schema above.
"""
