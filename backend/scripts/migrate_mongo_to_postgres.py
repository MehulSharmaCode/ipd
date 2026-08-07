"""
MongoDB to PostgreSQL Data Migration Script
--------------------------------------------
Migrates farmers, schemes, and documents from MongoDB to PostgreSQL relational tables.
Usage:
  python -m scripts.migrate_mongo_to_postgres
"""

import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.models_sql import Base, Farmer, Scheme, FarmerDocument, AuditLog
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/agrisense_db")

async def migrate():
    logger.info("Starting MongoDB -> PostgreSQL Migration...")
    
    # 1. Connect to MongoDB
    mongo_client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client[settings.DATABASE_NAME]

    # 2. Connect to PostgreSQL
    engine = create_async_engine(POSTGRES_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Ensured PostgreSQL database tables exist.")

    async with async_session() as session:
        # Migrate Farmers
        farmer_docs = await mongo_db["farmers"].find().to_list(1000)
        logger.info(f"Found {len(farmer_docs)} farmers in MongoDB.")
        
        for doc in farmer_docs:
            fid = str(doc.get("_id"))
            existing = await session.get(Farmer, fid)
            if not existing:
                farmer = Farmer(
                    id=fid,
                    full_name=doc.get("full_name", "Unknown Farmer"),
                    email=doc.get("email", f"{fid}@agrisense.local"),
                    hashed_password=doc.get("hashed_password", "pbkdf2:sha256$default"),
                    phone_number=doc.get("phone_number"),
                    age=doc.get("age"),
                    gender=doc.get("gender"),
                    category=doc.get("category"),
                    state=doc.get("state"),
                    district=doc.get("district"),
                    taluka=doc.get("taluka"),
                    village=doc.get("village"),
                    land_size_hectares=doc.get("land_size_hectares"),
                    land_gat_number=doc.get("land_gat_number"),
                    soil_type=doc.get("soil_type"),
                    irrigation_type=doc.get("irrigation_type"),
                    primary_crops=doc.get("primary_crops", []),
                    farmer_type=doc.get("farmer_type"),
                    annual_income=doc.get("annual_income"),
                    is_differently_abled=doc.get("is_differently_abled", False),
                    bank_account_linked=doc.get("bank_account_linked", False),
                    is_aadhar_verified=doc.get("is_aadhar_verified", False),
                    aadhar_number=doc.get("aadhar_number"),
                    aadhar_last4=doc.get("aadhar_last4"),
                    is_pan_verified=doc.get("is_pan_verified", False),
                    pan_number=doc.get("pan_number"),
                    is_land_record_verified=doc.get("is_land_record_verified", False),
                    profile_wizard_complete=doc.get("profile_wizard_complete", False),
                )
                session.add(farmer)
        
        # Migrate Schemes
        scheme_docs = await mongo_db["schemes"].find().to_list(1000)
        logger.info(f"Found {len(scheme_docs)} schemes in MongoDB.")

        for doc in scheme_docs:
            code = doc.get("scheme_code")
            if code:
                existing_scheme = await session.get(Scheme, code)
                if not existing_scheme:
                    scheme = Scheme(
                        scheme_code=code,
                        name=doc.get("name", code),
                        level=doc.get("level", "central"),
                        state=doc.get("state"),
                        category=doc.get("category"),
                        description=doc.get("description"),
                        benefit_type=doc.get("benefit_type"),
                        benefit_calculation=doc.get("benefit_calculation"),
                        eligibility_rules=doc.get("rules", []),
                        source_url=doc.get("source_url"),
                        status=doc.get("status", "published"),
                    )
                    session.add(scheme)

        await session.commit()
        logger.info("MongoDB -> PostgreSQL Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
