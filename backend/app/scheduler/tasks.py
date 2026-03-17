
"""Background Scheduled Tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.matcher import MatcherService
from app.services.email_service import EmailService
from app.services.vectorizer import VectorizerService
from app.models import Opportunity, JobVector
import json

def generate_job_vectors():
    """Generate TF-IDF vectors for new jobs"""
    db = SessionLocal()
    try:
        # Get jobs without vectors
        jobs_without_vectors = db.query(Opportunity).outerjoin(JobVector).filter(
            JobVector.job_vector_id == None
        ).all()
        
        if not jobs_without_vectors:
            print("No new jobs to vectorize")
            return
        
        vectorizer = VectorizerService()
        
        # Prepare all job texts
        texts = []
        for job in jobs_without_vectors:
            text = vectorizer.prepare_text(
                role=job.role or "",
                skills=job.skills or "",
                company=job.company_name or ""
            )
            texts.append(text)
        
        # Generate vectors
        vectors = vectorizer.fit_transform_corpus(texts)
        
        # Save to database
        for job, vector in zip(jobs_without_vectors, vectors):
            job_vector = JobVector(
                job_id=job.id,
                vector_data=json.dumps(vector.tolist())
            )
            db.add(job_vector)
        
        db.commit()
        print(f"Generated vectors for {len(jobs_without_vectors)} jobs")
        
    finally:
        db.close()

def match_and_notify():
    """Match users with jobs and send notifications"""
    db = SessionLocal()
    try:
        matcher = MatcherService(db)
        matcher.match_all_users_with_new_jobs(threshold=0.75)
        
        email_service = EmailService()
        email_service.send_job_match_notification(db)
        
    finally:
        db.close()

def start_scheduler():
    """Start background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Run job vectorization every hour
    scheduler.add_job(generate_job_vectors, 'interval', hours=1)
    
    # Run matching and notifications every 2 hours
    scheduler.add_job(match_and_notify, 'interval', hours=2)
    
    scheduler.start()
    print("✅ Scheduler started")