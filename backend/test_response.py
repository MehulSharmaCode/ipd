import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.models.farmer import FarmerResponse

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["agrisense_db"]
    user = await db["farmers"].find_one({"email": "test@example.com"})
    
    if user:
        user["_id"] = str(user["_id"])
        print("User Dict:", user)
        try:
            resp = FarmerResponse(**user)
            print("Pydantic Validation Passed!")
            print(resp.model_dump())
        except Exception as e:
            print("Pydantic Validation Failed:", str(e))

asyncio.run(main())
