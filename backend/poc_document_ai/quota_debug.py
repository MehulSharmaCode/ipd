# SDK Version: google-genai 2.16.0
# API endpoint: generativelanguage.googleapis.com (default for AI Studio keys)
# Model name: gemini-2.5-flash, gemini-2.0-flash
# Environment variable: GEMINI_API_KEY
# Client initialization: genai.Client(api_key=api_key)

"""
Quota Debug Script
==================
Minimal script to debug Gemini 429 RESOURCE_EXHAUSTED errors.
"""
import os
import sys
from google import genai
from google.genai.errors import APIError

def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("✗ GEMINI_API_KEY is missing")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    print("=== Configuration ===")
    print(f"SDK Version: google-genai 2.16.0")
    print("Endpoint: generativelanguage.googleapis.com (default)")
    
    # Try gemini-flash-latest instead of 2.5/2.0
    model_name = "gemini-flash-latest"
    print("\n=== Request ===")
    print(f"Model: {model_name}")
    print("Payload: 'Say Hello'")
    
    print("\n=== Response ===")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say Hello"
        )
        print("Success! (HTTP 200 OK)")
        print(response.text)
        print(f"\nModel actually used: {response.model_version if hasattr(response, 'model_version') else 'Unknown'}")
    except APIError as e:
        print("=== EXCEPTION CAUGHT ===")
        print(f"Exception Class: {e.__class__.__name__}")
        print(f"HTTP Status: {e.code}")
        print(f"Message: {e.message}")
        print(f"Status: {e.status}")
        print(f"Details: {e.details}")
        print("\nFull Exception:")
        print(e)
    except Exception as e:
        print("=== UNEXPECTED EXCEPTION ===")
        print(f"Class: {e.__class__.__name__}")
        print(str(e))

if __name__ == "__main__":
    main()
