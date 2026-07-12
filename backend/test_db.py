import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["agrisense"]
    user = await db["farmers"].find_one({"email": "test@example.com"})
    print("User found by email:", user)
    if user:
        user_by_id = await db["farmers"].find_one({"_id": ObjectId(str(user["_id"]))})
        print("User found by ObjectId:", user_by_id)

asyncio.run(main())
