from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Opportunity(Base):
    __tablename__ = 'opportunities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    opportunity_type = Column(String(50))  # 'job', 'internship', 'hackathon'
    application_start_date = Column(DateTime)
    application_end_date = Column(DateTime)
    skills = Column(Text)  # Comma-separated skills
    experience_required = Column(String(100))
    job_portal_name = Column(String(100), nullable=False)
    application_link = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Opportunity(company='{self.company_name}', role='{self.role}')>"

# Database connection
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
#DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD').replace('@','%40')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Create all tables"""
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully!")

def get_db_session():
    """Get database session"""
    return SessionLocal()