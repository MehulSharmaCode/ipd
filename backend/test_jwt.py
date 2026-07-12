import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
import sys

# simulate fast api logic
async def main():
    import requests
    # Login
    resp = requests.post("http://localhost:8999/api/auth/login", data={"username": "test@example.com", "password": "password123"})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
    token = resp.json().get("access_token")
    print("Token:", token)
    
    # Try me endpoint
    me_resp = requests.get("http://localhost:8999/api/farmers/me", headers={"Authorization": f"Bearer {token}"})
    print("Me Response:", me_resp.status_code, me_resp.text)

    # Let's decode it manually with the same config
    from app.core.config import settings
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print("Decoded payload:", payload)
        
        from bson import ObjectId
        user_id = payload.get("sub")
        
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.DATABASE_NAME]
        user = await db["farmers"].find_one({"_id": ObjectId(user_id)})
        print("User from DB:", user)
        
    except Exception as e:
        print("PyJWTError or other Exception:", str(e))
        import traceback
        traceback.print_exc()

asyncio.run(main())
