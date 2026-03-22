
"""Background Scheduled Tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.matcher import MatcherService
from app.services.email_service import EmailService
from app.services.vectorizer import VectorizerService
from app.models import Opportunity, JobVector, SimilarityScore, EmailNotification
import json
from datetime import datetime

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

def cleanup_expired_jobs():
    """
    Automatically remove expired jobs and their related data from the database
    This runs daily to keep the database clean
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        
        # Find expired jobs
        expired_jobs = db.query(Opportunity).filter(
            (Opportunity.application_end_date < now) & 
            (Opportunity.application_end_date != None)
        ).all()
        
        if not expired_jobs:
            print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] No expired jobs to cleanup")
            return
        
        expired_job_ids = [job.id for job in expired_jobs]
        total_expired = len(expired_job_ids)
        
        print(f"\n🗑️  [{now.strftime('%Y-%m-%d %H:%M:%S')}] Starting cleanup of {total_expired} expired jobs...")
        
        # Delete related similarity scores
        similarity_count = db.query(SimilarityScore).filter(
            SimilarityScore.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        
        # Delete related email notifications
        email_count = db.query(EmailNotification).filter(
            EmailNotification.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        
        # Delete related job vectors
        vector_count = db.query(JobVector).filter(
            JobVector.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        
        # Delete the expired jobs
        db.query(Opportunity).filter(
            Opportunity.id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        
        # Commit all deletions
        db.commit()
        
        total_deleted = similarity_count + email_count + vector_count + total_expired
        print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] Cleanup completed!")
        print(f"   • Expired jobs removed: {total_expired}")
        print(f"   • Related records deleted: {total_deleted}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

def start_scheduler():
    """Start background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Run job vectorization every hour
    scheduler.add_job(generate_job_vectors, 'interval', hours=1)
    
    # Run matching and notifications every 2 hours
    scheduler.add_job(match_and_notify, 'interval', hours=2)
    
    # Run cleanup of expired jobs every 24 hours (daily)
    scheduler.add_job(cleanup_expired_jobs, 'interval', hours=24)
    
    scheduler.start()
    print("✅ Scheduler started with automatic expired job cleanup")