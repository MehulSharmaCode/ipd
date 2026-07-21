# backend/app/core/security.py
import logging
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
import bcrypt
import jwt
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

# This tells FastAPI where our login route is
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=1440) # 24 hours
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the token to get the user ID (sub)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        logger.debug("Token decoded successfully.")
        if user_id is None:
            logger.warning("Token missing 'sub' claim.")
            raise credentials_exception
    except jwt.PyJWTError as e:
        logger.warning(f"Token validation failed: {type(e).__name__}")
        raise credentials_exception

    db = get_db()
    # Find the user in the database
    from bson import ObjectId
    try:
        user = await db["farmers"].find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        logger.warning(f"Invalid ObjectId format in token: {type(e).__name__}")
        raise credentials_exception

    if user is None:
        logger.warning("Authenticated user not found in database.")
        raise credentials_exception

    user["_id"] = str(user["_id"])
    return user