# backend/app/api/monitoring.py
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File
from typing import List, Dict

from app.services.scheme_monitor import SchemeMonitor
from app.ml.policy_engine.policy_ingestor import PolicyIngestor
from app.core.security import get_current_user
from app.ml.ocr.ocr_service import verify_tesseract
from app.ml.ocr.config import get_config_summary

router = APIRouter(tags=["Monitoring & Automation"])


@router.get("/ocr-health")
async def ocr_health_check():
    """
    Verify that the OCR engine (Tesseract) is accessible.
    Returns full diagnostic information including detection method and version.
    """
    summary = get_config_summary()
    return {
        "status": "ok" if summary["tesseract_available"] else "unavailable",
        **summary,
    }


@router.get("/system-status")
async def get_system_status():
    """Returns the latest monitored schemes and status."""
    data = SchemeMonitor.scrape_latest_schemes()
    return {"status": "ok", "recent_updates": data}

@router.post("/refresh-schemes")
async def refresh_schemes(background_tasks: BackgroundTasks):
    """
    Triggers a background process to scrape and check for new schemes.
    Returns immediately, while the scraping happens asynchronously.
    """
    # In a full app, this would save to the DB. Here we just trigger the print/scrape.
    def background_scrape():
        print("🌍 Background Task: Starting proactive scheme monitor scrape...")
        data = SchemeMonitor.scrape_latest_schemes()
        print(f"🌍 Background Task: Found {len(data)} scheme updates.")
        # db.scheme_updates.insert_many(data) # Example DB persistence

    background_tasks.add_task(background_scrape)
    
    return {"message": "Scheme refresh initiated in the background."}

@router.post("/test/policy-ingest")
async def test_policy_ingest(
    file: UploadFile = File(...)
):
    """
    Test endpoint for uploading a PDF and synchronously running the AI Policy Intelligence Engine 
    to return extracted rules instantly for UI demonstration.
    """
    from app.ml.ocr.document_parser import BasicDocumentParser
    # 1. Read the PDF content directly in memory
    content = await file.read()
    
    # Simulate a scheme name from the filename
    scheme_name = file.filename.replace(".pdf", "").replace("_", " ")

    # 2. Extract raw text from the PDF
    # In a full app you'd parse better, here we use BasicDocumentParser
    try:
        raw_text = BasicDocumentParser.extract_text_from_pdf(content)
    except Exception as e:
        raw_text = "Simulated text for scheme eligibility: Minimum land size 1 hectare. Age must be below 60."
    
    # 3. Pass to the AI Policy Engine immediately (synchronously)
    extracted_rules = PolicyIngestor.extract_rules(raw_text)
    
    # 4. In a real system you'd save to DB here. For the test, we just return to UI.
    return {
        "message": f"Successfully ingested {scheme_name}",
        "extracted_rules": extracted_rules,
        "raw_text_snippet": raw_text[:200]
    }

@router.get("/schemes/latest")
async def get_latest_schemes():
    """
    Fetches the latest scraped scheme updates to show on the dashboard.
    """
    # Because our background task currently doesn't persist to a real DB collection
    # in this scoped example, we will just call the mock scraper synchronously for the UI to see data.
    data = SchemeMonitor.scrape_latest_schemes()
    return data

@router.post("/policy/ingest")
async def ingest_policy_document(
    scheme_name: str, 
    document_text: str, 
    background_tasks: BackgroundTasks
):
    """
    Simulates an admin uploading a new raw policy document text.
    The parsing and extraction of rules happens in the background.
    """
    background_tasks.add_task(
        PolicyIngestor.process_new_document, 
        document_text=document_text, 
        scheme_name=scheme_name
    )
    
    return {"message": f"Policy ingestion for '{scheme_name}' started in the background."}
