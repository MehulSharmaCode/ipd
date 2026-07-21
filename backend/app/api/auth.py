# backend/app/api/auth.py
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.models.farmer import FarmerSignup, FarmerResponse, Token
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/signup", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: FarmerSignup):
    db = get_db()
    
    # 1. Check if email already exists (normalized to lowercase)
    email_normalized = user_data.email.lower()
    existing_user = await db["farmers"].find_one({"email": email_normalized})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash the password
    hashed_pwd = get_password_hash(user_data.password)
    
    # 3. Prepare minimal data for Database
    farmer_dict = {
        "full_name": user_data.full_name,
        "email": email_normalized,
        "hashed_password": hashed_pwd,
        # Default empty lists/booleans for when they fill it out later
        "primary_crops": [],
        "documents_uploaded": [],
        "is_differently_abled": False,
        "bank_account_linked": False
    }
    
    # 4. Save to DB
    result = await db["farmers"].insert_one(farmer_dict)
    
    # 5. Fetch and return
    new_user = await db["farmers"].find_one({"_id": result.inserted_id})
    new_user["_id"] = str(new_user["_id"])
    logger.info("New farmer registered successfully.")
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    
    # In FastAPI OAuth2, the 'username' field will now hold our EMAIL
    # Normalize to lowercase and strip whitespace for case-insensitive lookup
    email_normalized = form_data.username.lower().strip()
    logger.debug("Login attempt received.")
    
    user = await db["farmers"].find_one({"email": email_normalized})
    
    if not user:
        logger.warning("Login failed: email not found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug("User located. Verifying password.")
    if not verify_password(form_data.password, user["hashed_password"]):
        logger.warning("Login failed: password mismatch.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Login successful.")
    # Generate JWT Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}