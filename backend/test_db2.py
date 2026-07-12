import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["agrisense_db"]
    user = await db["farmers"].find_one({"email": "test@example.com"})
    print("User found by email:", user)
    if user:
        user_id_str = str(user["_id"])
        print(f"User ID string: {user_id_str}")
        user_by_id = await db["farmers"].find_one({"_id": ObjectId(user_id_str)})
        print("User found by ObjectId:", user_by_id)

asyncio.run(main())
