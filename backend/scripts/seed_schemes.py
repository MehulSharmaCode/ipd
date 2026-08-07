import asyncio
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend root directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

RULES_PATH = backend_dir / "app" / "ml" / "rules" / "schemes_rules.yaml"


async def seed_schemes():
    print(f"Connecting to MongoDB at {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[settings.DATABASE_NAME]

    try:
        await db.command("ping")
        print("Connected to MongoDB successfully.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    schemes_collection = db["schemes"]

    if not RULES_PATH.exists():
        print(f"Rules YAML file not found at: {RULES_PATH}")
        return

    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    raw_schemes = data.get("schemes", [])
    print(f"Loaded {len(raw_schemes)} schemes from {RULES_PATH.name}")

    seeded_count = 0
    updated_count = 0

    for scheme in raw_schemes:
        scheme_id = scheme.get("scheme_id")
        if not scheme_id:
            continue

        existing = await schemes_collection.find_one({"scheme_id": scheme_id})
        
        doc = {
            "scheme_id": scheme_id,
            "name": scheme.get("name", scheme_id),
            "department": scheme.get("department", "Ministry of Agriculture & Farmers Welfare"),
            "description": scheme.get("description", f"Support scheme {scheme_id}"),
            "category": scheme.get("category", "Financial Support"),
            "level": scheme.get("level", "central"),
            "state": scheme.get("state"),
            "benefit_type": scheme.get("benefit_type", "Direct Benefit Transfer"),
            "benefit_calculation": scheme.get("benefit_calculation", {"type": "flat_rate", "base_rate": 5000}),
            "conflicts_with": scheme.get("conflicts_with", []),
            "rules": scheme.get("rules", []),
            "status": scheme.get("status", "published"),
            "source_url": scheme.get("source_url"),
            "updated_at": datetime.utcnow()
        }

        if existing:
            await schemes_collection.update_one({"scheme_id": scheme_id}, {"$set": doc})
            updated_count += 1
        else:
            doc["created_at"] = datetime.utcnow()
            await schemes_collection.insert_one(doc)
            seeded_count += 1

    print(f"Seeding complete! New schemes inserted: {seeded_count}, existing updated: {updated_count}")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_schemes())
