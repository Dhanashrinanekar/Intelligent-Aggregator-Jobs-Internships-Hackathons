
"""Pydantic Schemas for Request/Response Validation"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ============ User Schemas ============
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
    skills: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Token Schemas ============
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ============ Job Schemas ============
class JobResponse(BaseModel):
    id: int
    company_name: str
    role: str
    opportunity_type: str
    skills: Optional[str] = None
    experience_required: Optional[str] = None
    job_portal_name: str
    application_link: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class JobSearchParams(BaseModel):
    keyword: Optional[str] = None
    opportunity_type: Optional[str] = None
    portal: Optional[str] = None
    page: int = 1
    limit: int = 20

# ============ Recommendation Schemas ============
class RecommendationResponse(BaseModel):
    job_id: int
    company_name: str
    role: str
    opportunity_type: str
    skills: Optional[str]
    similarity_score: float
    rank_position: int
    application_link: str
    
    class Config:
        from_attributes = True

# ============ Resume Schemas ============
class ResumeUploadResponse(BaseModel):
    message: str
    skills_extracted: List[str]
    matches_found: int

# ============ OTP Schemas ============
class SendOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    name: Optional[str] = None
    password: Optional[str] = None

class OTPResponse(BaseModel):
    message: str
    email: str