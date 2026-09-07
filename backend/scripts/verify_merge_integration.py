#!/usr/bin/env python3
"""
Merge Integration Verification
================================
Regression suite for the feature/gemini-7-12-integration ->
feature/agri-platform-updates merge resolution
(backend/app/api/upload.py, document_processing/{vision/__init__.py,
profile_builder.py}, ml/ocr/{classification,parsers,preprocessing}.py).

Covers two tiers:
  PHASE 1 — Unit tests (no server/DB/network): classification keyword
            union, Aadhaar parser two/three-pass extraction, document
            router alias registration, ProfileBuilder derived-field logic.
  PHASE 2 — Live integration (needs MongoDB + a real GEMINI_API_KEY in
            backend/.env): boots the real FastAPI app in a subprocess,
            signs up a throwaway user, uploads the committed
            backend/samples/satbara/satbara1.jpeg through the legacy
            "satbara" alias, and asserts the extracted + persisted
            farmer profile matches what both merged branches expected
            (land_size_hectares as a float, state="Maharashtra",
            is_7_12_verified=True, village/taluka present).

Phase 2 test data (the throwaway signup account) is deleted from
MongoDB at the end of the run, pass or fail.

Usage:
  cd backend
  python scripts/verify_merge_integration.py
  python scripts/verify_merge_integration.py --unit-only   # skip Phase 2

Returns exit code 0 on success, 1 on failure.
"""

import sys
import os
import time
import subprocess
import atexit

# ── Bootstrap: add backend root to sys.path ────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(script_dir)
sys.path.insert(0, backend_root)
os.chdir(backend_root)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BOLD, GREEN, RED, CYAN, YELLOW, RESET = (
    "\033[1m", "\033[32m", "\033[31m", "\033[36m", "\033[33m", "\033[0m"
)

def ok(msg):   print(f"  {GREEN}[OK]{RESET} {msg}")
def fail(msg): print(f"  {RED}[FAIL]{RESET} {msg}")
def info(msg): print(f"  {CYAN}[..]{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}[WARN]{RESET} {msg}")
def section(title):
    print(f"\n{BOLD}{CYAN}{'-'*60}{RESET}\n{BOLD} {title}{RESET}\n{'-'*60}")

FAILURES = []

def check(condition: bool, description: str):
    if condition:
        ok(description)
    else:
        fail(description)
        FAILURES.append(description)


# ════════════════════════════════════════════════════════════════════
# PHASE 1 — Unit tests
# ════════════════════════════════════════════════════════════════════

def run_phase1():
    section("Phase 1: Unit tests (classification, parsers, router, profile builder)")

    from app.ml.ocr.classification import classify
    from app.ml.ocr.parsers import AadhaarParser

    # -- 1a. Classification keyword union (agri-platform + gemini-7-12 merged) --
    text_front = "GOVERNMENT OF INDIA\nUIDAI\nDOB: 15/08/1990\nMALE\nVID: 1234"
    result = classify(text_front)
    check(result.document_type == "AADHAAR_FRONT",
          f"classify(): AADHAAR_FRONT keywords detect correctly (got {result.document_type})")
    check("VID" in result.matched_keywords,
          "classify(): theirs' 'VID' keyword survived the union merge")

    # -- 1b. Aadhaar number: strict two-pass path (gemini-7-12 branch) --
    clean_text = "GOVERNMENT OF INDIA\n234567890123\nDOB: 15/08/1990\nMALE"
    r = AadhaarParser().extract(clean_text)
    check(r.get("aadhaarNumber") == "2345 6789 0123",
          f"AadhaarParser: clean two-pass extraction (got {r.get('aadhaarNumber')!r})")

    # -- 1c. Aadhaar number: fuzzy fallback (agri-platform branch, re-added as pass 3) --
    fuzzy_text = "GOVERNMENT OF INDIA\n234S 6789 O123\nDOB: 15/08/1990\nMALE"
    r2 = AadhaarParser().extract(fuzzy_text)
    check(r2.get("aadhaarNumber") == "2345 6789 0123",
          f"AadhaarParser: fuzzy OCR-correction fallback recovers number (got {r2.get('aadhaarNumber')!r})")

    # -- 1d. Birth-year fallback: theirs' group()->ValueError bug, fixed to group(1) --
    year_only_text = "GOVERNMENT OF INDIA\nDOB: 1985\nMALE"
    try:
        r3 = AadhaarParser().extract(year_only_text)
        check(r3.get("birthYear") == "1985",
              f"AadhaarParser: 'DOB: 1985' birth-year fallback (got {r3.get('birthYear')!r})")
    except ValueError as e:
        fail(f"AadhaarParser: 'DOB: 1985' raised ValueError (latent merge bug not fixed): {e}")
        FAILURES.append("birth-year fallback ValueError")

    # -- 1e. Document router: legacy aliases registered alongside canonical '7_12' --
    import app.document_processing.ocr    # noqa: F401 — registers aadhar/pan
    import app.document_processing.vision  # noqa: F401 — registers 7_12 + aliases
    from app.document_processing.router import document_router
    expected_keys = {"aadhar", "aadhaar", "pan", "7_12", "satbara", "satbara_7_12"}
    registered = set(document_router.supported_types)
    check(expected_keys.issubset(registered),
          f"DocumentRouter: all expected doc_type keys registered (missing: {expected_keys - registered})")

    # -- 1f. ProfileBuilder: land_size_hectares/state/aadhar_last4 restored (upload.py fix) --
    from app.document_processing.schemas import ExtractionResult
    from app.document_processing.profile_builder import FarmerProfileBuilder

    builder = FarmerProfileBuilder()

    land_result = ExtractionResult(document_type="7_12", success=True)
    land_result.set_field("owner_name", "Test Owner", confidence=0.85)
    land_result.set_field("village", "Testvillage", confidence=0.85)
    land_result.set_field("taluka", "Testtaluka", confidence=0.85)
    land_result.set_field("land_area", "6.11", confidence=0.85)
    land_result.validation = {"valid": True, "warnings": []}
    update = builder.build_update(land_result)

    check(update.get("land_size_hectares") == 6.11 and isinstance(update.get("land_size_hectares"), float),
          f"ProfileBuilder: land_size_hectares derived as float from land_area (got {update.get('land_size_hectares')!r})")
    check(update.get("state") == "Maharashtra",
          f"ProfileBuilder: state defaulted to Maharashtra for 7_12 doc_type (got {update.get('state')!r})")
    check(update.get("is_7_12_verified") is True,
          "ProfileBuilder: is_7_12_verified flag set (matches models/farmer.py, not is_land_record_verified)")

    aadhaar_result = ExtractionResult(document_type="aadhar", success=True)
    aadhaar_result.set_field("aadhar_number", "2345 6789 0123", confidence=0.9)
    aadhaar_result.validation = {"valid": True, "warnings": []}
    aadhaar_update = builder.build_update(aadhaar_result)
    check(aadhaar_update.get("aadhar_last4") == "0123",
          f"ProfileBuilder: aadhar_last4 derived (got {aadhaar_update.get('aadhar_last4')!r})")

    bad_result = ExtractionResult(document_type="7_12", success=True)
    bad_result.set_field("village", "X", confidence=0.85)
    bad_result.set_field("land_area", "not-a-number", confidence=0.85)
    bad_result.validation = {"valid": False, "warnings": ["x"]}
    bad_update = builder.build_update(bad_result)
    check("land_size_hectares" not in bad_update,
          "ProfileBuilder: unparseable land_area skipped instead of raising")


# ════════════════════════════════════════════════════════════════════
# PHASE 2 — Live integration (server + MongoDB + real Gemini call)
# ════════════════════════════════════════════════════════════════════

TEST_PORT = 8123
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"
_server_proc = None
_test_email = None


def _stop_server():
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _server_proc.kill()


def _cleanup_test_user():
    if not _test_email:
        return
    try:
        import pymongo
        from app.core.config import Settings
        settings = Settings()
        client = pymongo.MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[settings.DATABASE_NAME]
        res = db["farmers"].delete_one({"email": _test_email})
        if res.deleted_count:
            info(f"Cleaned up throwaway test account ({_test_email})")
    except Exception as e:
        warn(f"Could not clean up test account: {e}")


atexit.register(_stop_server)
atexit.register(_cleanup_test_user)


def run_phase2():
    global _server_proc, _test_email

    section("Phase 2: Live integration (real server, MongoDB, Gemini API)")

    sample_path = os.path.join(backend_root, "samples", "satbara", "satbara1.jpeg")
    if not os.path.isfile(sample_path):
        warn(f"Sample file not found at {sample_path} — skipping Phase 2")
        return

    from dotenv import load_dotenv
    load_dotenv(os.path.join(backend_root, ".env"))
    if not os.getenv("GEMINI_API_KEY", "").strip():
        warn("GEMINI_API_KEY is empty in backend/.env — skipping Phase 2 (live Gemini call)")
        return

    try:
        import requests
    except ImportError:
        warn("'requests' not installed — skipping Phase 2")
        return

    import pymongo
    from app.core.config import Settings
    settings = Settings()
    try:
        mongo_client = pymongo.MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
        mongo_client.admin.command("ping")
    except Exception as e:
        warn(f"MongoDB not reachable at {settings.MONGO_URI} — skipping Phase 2 ({e})")
        return

    info(f"Starting test server on {BASE_URL} ...")
    env = os.environ.copy()
    server_log_path = os.path.join(backend_root, "scripts", "_verify_server.log")
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    _server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(TEST_PORT)],
        cwd=backend_root, env=env,
        stdout=server_log_file, stderr=subprocess.STDOUT, text=True,
    )

    deadline = time.time() + 30
    up = False
    while time.time() < deadline:
        try:
            r = requests.get(BASE_URL + "/", timeout=1)
            if r.status_code == 200:
                up = True
                break
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    check(up, "Test server started and is reachable")
    if not up:
        server_log_file.flush()
        with open(server_log_path, encoding="utf-8", errors="replace") as f:
            print(f.read()[-2000:])
        return

    # -- Signup + login a throwaway account --
    _test_email = f"merge_verify_{int(time.time())}@example.com"
    signup_resp = requests.post(
        f"{BASE_URL}/api/auth/signup",
        json={"full_name": "Merge Verify", "email": _test_email, "password": "TestPass123!"},
        timeout=10,
    )
    check(signup_resp.status_code in (200, 201), f"Signup succeeded (status={signup_resp.status_code})")

    login_resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": _test_email, "password": "TestPass123!"},
        timeout=10,
    )
    check(login_resp.status_code == 200, f"Login succeeded (status={login_resp.status_code})")
    token = login_resp.json().get("access_token")
    check(bool(token), "Login returned an access_token")
    if not token:
        return
    headers = {"Authorization": f"Bearer {token}"}

    # -- Upload the sample 7/12 via the legacy 'satbara' alias --
    info("Uploading samples/satbara/satbara1.jpeg via legacy 'satbara' doc_type alias "
         "(live Gemini Vision call — this can take up to a couple of minutes)...")
    try:
        with open(sample_path, "rb") as f:
            upload_resp = requests.post(
                f"{BASE_URL}/api/upload/",
                headers=headers,
                files={"file": ("satbara1.jpeg", f, "image/jpeg")},
                data={"doc_type": "satbara"},
                timeout=240,
            )
    except requests.exceptions.RequestException as e:
        fail(f"Upload request failed/timed out (Gemini API latency, not a merge-resolution bug): {e}")
        FAILURES.append("upload request failed/timed out")
        server_log_file.flush()
        with open(server_log_path, encoding="utf-8", errors="replace") as f:
            info("Server log tail:")
            print(f.read()[-3000:])
        return

    check(upload_resp.status_code == 200,
          f"Upload via 'satbara' alias succeeded (status={upload_resp.status_code}, "
          f"body={upload_resp.text[:300] if upload_resp.status_code != 200 else 'OK'})")

    if upload_resp.status_code == 200:
        body = upload_resp.json()
        fields = body.get("fields", {})
        check(body.get("documentType") == "7_12",
              f"Extraction result document_type == '7_12' (got {body.get('documentType')!r})")
        check(bool(fields), f"Gemini extracted at least one field (got {len(fields)} fields)")
        for key in ("owner_name", "village", "land_area"):
            present = key in fields and fields[key].get("value") not in (None, "")
            check(present, f"Gemini extraction includes '{key}'"
                  + ("" if present else f" (fields returned: {list(fields.keys())})"))

    # -- Verify what actually landed in MongoDB --
    db = mongo_client[settings.DATABASE_NAME]
    farmer = db["farmers"].find_one({"email": _test_email})
    check(farmer is not None, "Farmer document exists in MongoDB after upload")
    if farmer:
        lsh = farmer.get("land_size_hectares")
        check(isinstance(lsh, float) and lsh > 0,
              f"MongoDB: land_size_hectares persisted as a float (got {lsh!r} / {type(lsh).__name__}) "
              "— this is the critical fix restored in profile_builder.py")
        check(farmer.get("state") == "Maharashtra",
              f"MongoDB: state == 'Maharashtra' (got {farmer.get('state')!r})")
        check(farmer.get("is_7_12_verified") is True,
              f"MongoDB: is_7_12_verified == True (got {farmer.get('is_7_12_verified')!r})")
        check("is_land_record_verified" not in farmer,
              "MongoDB: legacy 'is_land_record_verified' key NOT present (theirs' naming won)")


# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unit_only = "--unit-only" in sys.argv

    run_phase1()
    if not unit_only:
        try:
            run_phase2()
        finally:
            _stop_server()
            _cleanup_test_user()

    section("Summary")
    if FAILURES:
        fail(f"{len(FAILURES)} check(s) failed:")
        for f in FAILURES:
            print(f"      - {f}")
        sys.exit(1)
    else:
        ok("All checks passed.")
        sys.exit(0)
