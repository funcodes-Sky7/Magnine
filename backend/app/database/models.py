"""
MANGANAI Backend - Database Models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FieldValidation(Base):
    __tablename__ = "field_validations"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(String(20), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    sample_id = Column(String(50))
    mn_grade = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    lithology = Column(String(200), nullable=True)
    result = Column(String(50))  # confirmed / not_found / inconclusive
    notes = Column(Text, nullable=True)
    photo_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, index=True)
    algorithm = Column(String(50))
    training_samples = Column(Integer)
    validated_samples = Column(Integer)
    feature_count = Column(Integer)
    f1_score = Column(Float)
    recall = Column(Float)
    precision = Column(Float)
    accuracy = Column(Float)
    features = Column(JSON)
    feature_importance = Column(JSON)
    is_active = Column(Boolean, default=False)
    model_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(String(20), unique=True, index=True)
    name = Column(String(100))
    priority = Column(String(20))  # HIGH / MODERATE / LOW
    prospectivity = Column(Float)
    confidence = Column(Float)
    risk = Column(String(20))
    lat = Column(Float)
    lng = Column(Float)
    area_km2 = Column(Float)
    depth_min = Column(Integer)
    depth_max = Column(Integer)
    geology = Column(String(200))
    state = Column(String(100))
    evidence = Column(JSON)
    feature_contributions = Column(JSON)
    model_version = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class PredictionRun(Base):
    __tablename__ = "prediction_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String(20))
    status = Column(String(20))  # running / complete / failed
    target_count = Column(Integer, nullable=True)
    high_priority_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
