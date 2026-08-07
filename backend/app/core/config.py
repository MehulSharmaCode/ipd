# backend/app/core/config.py
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class Settings:
    PROJECT_NAME: str = "AgriSense"
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "agrisense_db")
    
    # Security Auth settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "agrisense_hackathon_secret_key_2026_binary_brains_secure")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

    # myScheme.gov.in API
    MYSCHEME_API_KEY: str = os.getenv("MYSCHEME_API_KEY", "")
    MYSCHEME_API_BASE: str = os.getenv("MYSCHEME_API_BASE", "https://api.myscheme.gov.in")

    def __init__(self):
        if self.SECRET_KEY in {"fallback_secret_key", "change_me_in_production"}:
            logger.warning("SECURITY WARNING: Using default fallback SECRET_KEY. Set a strong secret key in .env for production!")

settings = Settings()