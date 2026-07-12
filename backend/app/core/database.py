from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class Database:
    client: AsyncIOMotorClient | None = None
    db = None


db_instance = Database()


# ================================
# Connect to MongoDB
# ================================
async def connect_to_mongo():
    print("Connecting to MongoDB...")
    
    # Added timeout so we don't wait forever if DB is down
    db_instance.client = AsyncIOMotorClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=5000 
    )
    
    db_instance.db = db_instance.client[settings.DATABASE_NAME]
    
    try:
        # The 'ping' command is cheap and verifies that the server is actually reachable
        await db_instance.db.command("ping")
        print(f"Successfully connected to database: {settings.DATABASE_NAME}!")
    except Exception as e:
        print(f"ERROR: Could not connect to MongoDB at {settings.MONGO_URI}. Is the service running?")
        print(f"Details: {e}")
        # We don't raise here to allow the app to 'start' but it will be obvious why it fails later


# ================================
# Close MongoDB Connection
# ================================
async def close_mongo_connection():
    print("Closing MongoDB connection...")

    if db_instance.client:
        db_instance.client.close()
        print("MongoDB connection closed.")


# ================================
# Get Database Anywhere
# ================================
def get_db():
    return db_instance.db


# ================================
# Shortcut (optional but useful)
# ================================
def get_collection(name: str):
    return db_instance.db[name]