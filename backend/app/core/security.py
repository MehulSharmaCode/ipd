# backend/app/core/security.py
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
import bcrypt
import jwt
from app.core.config import settings
from app.core.database import get_db

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

# --- NEW: Get Current Logged-In User ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # DEBUG: Print the received token
    print(f"🕵️ DEBUG: get_current_user received token: {token[:20]}...{token[-10:]}" if token else "🕵️ DEBUG: get_current_user received EMPTY token!")

    try:
        # Decode the token to get the user ID (sub)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        print(f"🕵️ DEBUG: Decoded payload: {payload}, user_id: {user_id}")
        if user_id is None:
            print("🕵️ DEBUG: Token missing 'sub' claim!")
            raise credentials_exception
    except jwt.PyJWTError as e:
        print(f"🕵️ DEBUG: PyJWTError decoding token: {e}")
        raise credentials_exception
        
    db = get_db()
    # Find the user in the database
    from bson import ObjectId
    try:
        user = await db["farmers"].find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        print(f"🕵️ DEBUG: Error parsing ObjectId '{user_id}': {e}")
        raise credentials_exception

    if user is None:
        print(f"🕵️ DEBUG: User not found in DB for ID {user_id}!")
        raise credentials_exception
        
    user["_id"] = str(user["_id"])
    return user