"""
Complete SQLAlchemy Models for AI Job Aggregator
Maps to exact database schema provided
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model - stores user profile and resume"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Hashed
    skills = Column(Text)  # Comma-separated
    resume_file = Column(String(500))  # File path
    resume_text = Column(Text)  # Extracted text
    is_verified = Column(Boolean, default=False)  # Email verification status
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    resume_vector = relationship("ResumeVector", back_populates="user", uselist=False, cascade="all, delete-orphan")
    similarity_scores = relationship("SimilarityScore", back_populates="user", cascade="all, delete-orphan")
    email_notifications = relationship("EmailNotification", back_populates="user", cascade="all, delete-orphan")
    otp_codes = relationship("OTPCode", back_populates="user", cascade="all, delete-orphan")


class Opportunity(Base):
    """Job/Opportunity model - maps to your existing opportunities table"""
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), index=True)
    role = Column(String(500), index=True)
    opportunity_type = Column(String(100))  # job/internship
    application_start_date = Column(DateTime(timezone=True))
    application_end_date = Column(DateTime(timezone=True))
    skills = Column(Text)  # Comma-separated
    experience_required = Column(String(100))
    job_portal_name = Column(String(100))
    application_link = Column(String(1000), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    job_vector = relationship("JobVector", back_populates="job", uselist=False, cascade="all, delete-orphan")
    similarity_scores = relationship("SimilarityScore", back_populates="job", cascade="all, delete-orphan")
    email_notifications = relationship("EmailNotification", back_populates="job", cascade="all, delete-orphan")


class ResumeVector(Base):
    """Resume TF-IDF vector storage"""
    __tablename__ = "resume_vector"
    
    vector_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    vector_data = Column(Text, nullable=False)  # JSON string of vector
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="resume_vector")


class JobVector(Base):
    """Job TF-IDF vector storage"""
    __tablename__ = "job_vector"
    
    job_vector_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), unique=True, nullable=False)
    vector_data = Column(Text, nullable=False)  # JSON string of vector
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("Opportunity", back_populates="job_vector")


class SimilarityScore(Base):
    """Resume-Job similarity scores"""
    __tablename__ = "similarity_score"
    
    match_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    similarity_score = Column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    rank_position = Column(Integer)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    email_sent = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="similarity_scores")
    job = relationship("Opportunity", back_populates="similarity_scores")


class EmailNotification(Base):
    """Track sent email notifications"""
    __tablename__ = "email_notifications"
    
    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    similarity_score = Column(Numeric(5, 4), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    email_status = Column(String(50), default='sent')  # sent, failed, pending
    
    # Relationships
    user = relationship("User", back_populates="email_notifications")
    job = relationship("Opportunity", back_populates="email_notifications")


class OTPCode(Base):
    """OTP Verification Code"""
    __tablename__ = "otp_codes"
    
    otp_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    email = Column(String(255), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="otp_codes")