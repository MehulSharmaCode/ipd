# backend/app/document_processing/__init__.py
"""
Intelligent Document Processing Engine
========================================
Single entry point for all uploaded documents (Aadhaar, PAN, 7/12, future types).

Modules:
  schemas.py      — Standardised extraction schema (contract for all processors)
  interfaces.py   — DocumentProcessor protocol
  router.py       — Routes doc_type to the correct processor
  ocr/            — Aadhaar & PAN adapters wrapping the existing Tesseract pipeline
  vision/         — Gemini 7/12 pipeline (ported from validated PoC)
  profile_builder — Merges multi-document extractions into a unified FarmerProfile
  validator       — Cross-document conflict detection
"""
