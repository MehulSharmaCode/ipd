"""
List Gemini Models
==================
Diagnostics script to list all available models for the configured API key.
Saves the complete output to available_models.txt.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent
_env_path = _backend_dir / ".env"
load_dotenv(dotenv_path=_env_path)

def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("✗ GEMINI_API_KEY is missing or empty in", _env_path)
        sys.exit(1)
        
    try:
        from google import genai
    except ImportError:
        print("✗ google-genai SDK is not installed.")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
    except Exception as exc:
        print(f"✗ Failed to create Gemini client: {exc}")
        sys.exit(1)
        
    output_file = Path(__file__).resolve().parent / "available_models.txt"
    
    print("Fetching models from Gemini API...")
    try:
        models = list(client.models.list())
        
        with open(output_file, "w") as f:
            for model in models:
                name = model.name
                # The GenAI SDK model object has attributes like supported_generation_methods, input_token_limit, etc.
                methods = getattr(model, "supported_generation_methods", [])
                
                # Check for modalities. In new SDK, they might not be directly exposed as input_modalities,
                # but let's try to extract what we can.
                f.write(f"Model name: {name}\n")
                f.write(f"Supported generation methods: {methods}\n")
                
                # Try to print out general attributes for diagnostic purposes
                for attr in dir(model):
                    if not attr.startswith("_") and attr not in ["name", "supported_generation_methods"]:
                        val = getattr(model, attr)
                        if not callable(val):
                            f.write(f"{attr}: {val}\n")
                
                f.write("-" * 50 + "\n")
        print(f"✓ Saved {len(models)} models to {output_file}")
    except Exception as exc:
        print(f"✗ Failed to list models: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    main()
