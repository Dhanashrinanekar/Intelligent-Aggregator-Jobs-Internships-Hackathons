"""Application Configuration"""
from pydantic_settings import BaseSettings
import os
from pathlib import Path

# Point to backend/.env regardless of working directory
ENV_FILE = Path(__file__).parent.parent / ".env"  # ← FIXED: __file__ not _file_

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/job_aggregator"
    
    # JWT
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Email SMTP
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    
    # File Upload
    UPLOAD_DIR: str = "uploads/resumes"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    # Matching
    SIMILARITY_THRESHOLD: float = 0.3
    
    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "allow"

settings = Settings()