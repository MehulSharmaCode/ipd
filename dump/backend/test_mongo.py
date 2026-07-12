import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_mongo():
    print("Testing MongoDB connection...")
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client["agrisense_db"]
        # Try a simple ping or list collections
        collections = await db.list_collection_names()
        print(f"Collections: {collections}")
        
        # Try an insert
        test_doc = {"test": "data"}
        res = await db["test_col"].insert_one(test_doc)
        print(f"Insert successful: {res.inserted_id}")
        
        # Clean up
        await db["test_col"].delete_one({"_id": res.inserted_id})
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"MongoDB Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_mongo())
