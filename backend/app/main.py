# backend/app/main.py
import os
import warnings

# Silence noisy ML warnings
os.environ["LOKY_MAX_CPU_COUNT"] = "4"  # Fix for wmic deprecation on Windows
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", category=UserWarning, module="joblib")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.documents import router as documents_router
from app.core.database import connect_to_mongo, close_mongo_connection
# Imported the new auth, upload, and stories routes here!
from app.api import farmers, auth, upload, stories

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up the server...")
    await connect_to_mongo()
    yield
    print("Shutting down the server...")
    await close_mongo_connection()

app = FastAPI(
    title="AgriSense API",
    description="Intelligent Scheme Discovery Platform for Farmers",
    version="1.0.0",
    lifespan=lifespan 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attached all routers to the main app
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(farmers.router, prefix="/api/farmers", tags=["Farmers"])
app.include_router(upload.router, prefix="/api/upload", tags=["Documents"])
app.include_router(stories.router, prefix="/api/stories", tags=["Community Stories"])
app.include_router(documents_router)  # Registered for ML-related document logic
from app.api.monitoring import router as monitoring_router
app.include_router(monitoring_router, prefix="/api/monitoring")


@app.get("/")
async def root():
    return {"message": "Welcome to the AgriSense API. System is operational."}