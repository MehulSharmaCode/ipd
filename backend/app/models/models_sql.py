"""
PostgreSQL Relational Database Schemas (SQLAlchemy ORM)
----------------────────────────────────────────────────
Tables created:
  - farmers
  - schemes
  - farmer_documents
  - farmer_scheme_matches
  - applications
  - crop_recommendations
  - audit_logs
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Text, Boolean, Float, Integer, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    state = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True, index=True)
    taluka = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    land_size_hectares = Column(Float, nullable=True)
    land_gat_number = Column(String(50), nullable=True)
    soil_type = Column(String(50), nullable=True)
    irrigation_type = Column(String(50), nullable=True)
    primary_crops = Column(JSON, nullable=True)
    farmer_type = Column(String(50), nullable=True)
    annual_income = Column(Float, nullable=True)
    is_differently_abled = Column(Boolean, default=False)
    bank_account_linked = Column(Boolean, default=False)

    # Verification status & PII
    is_aadhar_verified = Column(Boolean, default=False)
    aadhar_number = Column(String(50), nullable=True)
    aadhar_last4 = Column(String(4), nullable=True)

    is_pan_verified = Column(Boolean, default=False)
    pan_number = Column(String(20), nullable=True)

    is_land_record_verified = Column(Boolean, default=False)
    profile_wizard_complete = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("FarmerDocument", back_populates="farmer", cascade="all, delete-orphan")
    matches = relationship("FarmerSchemeMatch", back_populates="farmer", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="farmer", cascade="all, delete-orphan")
    crop_recommendations = relationship("CropRecommendation", back_populates="farmer", cascade="all, delete-orphan")


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    level = Column(String(20), nullable=False)   # 'central' or 'state'
    state = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    benefit_type = Column(String(50), nullable=True)
    benefit_calculation = Column(JSON, nullable=True)
    eligibility_rules = Column(JSON, nullable=True)
    source_url = Column(Text, nullable=True)
    status = Column(String(30), default="published", index=True)  # draft, pending_review, published
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    matches = relationship("FarmerSchemeMatch", back_populates="scheme", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="scheme", cascade="all, delete-orphan")


class FarmerDocument(Base):
    __tablename__ = "farmer_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False)  # aadhaar, pan, satbara_7_12
    file_path = Column(String(255), nullable=False)
    ocr_confidence = Column(Float, nullable=True)
    extracted_fields = Column(JSON, nullable=True)
    verification_status = Column(String(30), default="verified")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="documents")


class FarmerSchemeMatch(Base):
    __tablename__ = "farmer_scheme_matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    eligibility_score = Column(Float, nullable=False, default=1.0)
    bundle_rank = Column(Integer, nullable=True)
    calculated_benefit = Column(Float, nullable=True)
    matched_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="matches")
    scheme = relationship("Scheme", back_populates="matches")


class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="submitted", index=True) # submitted, under_review, approved, rejected
    application_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    farmer = relationship("Farmer", back_populates="applications")
    scheme = relationship("Scheme", back_populates="applications")


class CropRecommendation(Base):
    __tablename__ = "crop_recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True)
    recommended_crop = Column(String(100), nullable=False)
    confidence_score = Column(Float, nullable=False)
    season = Column(String(50), nullable=True)
    expected_yield_per_hectare = Column(Float, nullable=True)
    recommended_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="crop_recommendations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
