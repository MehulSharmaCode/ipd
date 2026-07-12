import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["agrisense_db"]
    farmers = await db["farmers"].find().to_list(10)
    
    print(f"Total farmers found: {len(farmers)}")
    for f in farmers:
        print(f"\nFarmer: {f.get('full_name')} ({f.get('email')})")
        # Print only relevant fields for privacy but enough to debug
        fields = ['annual_income', 'land_size_hectares', 'farmer_type', 'irrigation_type', 'primary_crops', 'state']
        for field in fields:
            val = f.get(field)
            print(f"  {field}: {val} ({type(val)})")

if __name__ == "__main__":
    asyncio.run(check_db())
