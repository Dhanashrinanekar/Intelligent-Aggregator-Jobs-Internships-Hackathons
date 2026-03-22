"""
Cleanup Script: Remove Expired Jobs from Database
This script removes jobs that have expired (application_end_date has passed)
"""

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Opportunity, SimilarityScore, EmailNotification, JobVector
from app.config import DATABASE_URL

def cleanup_expired_jobs():
    """
    Delete all expired jobs and their related data from the database
    Removes:
    - Jobs with expired application_end_date
    - Associated similarity scores
    - Associated email notifications
    - Associated job vectors
    """
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        now = datetime.now()
        
        print(f"🕐 Starting cleanup at {now.isoformat()}")
        print("=" * 60)
        
        # Find expired jobs
        expired_jobs = session.query(Opportunity).filter(
            (Opportunity.application_end_date < now) & 
            (Opportunity.application_end_date != None)
        ).all()
        
        if not expired_jobs:
            print("✅ No expired jobs found!")
            return
        
        expired_job_ids = [job.id for job in expired_jobs]
        total_expired = len(expired_job_ids)
        
        print(f"🔍 Found {total_expired} expired jobs:")
        for job in expired_jobs[:10]:  # Show first 10
            expiry = job.application_end_date.strftime("%Y-%m-%d %H:%M:%S")
            print(f"   • {job.role or 'N/A'} @ {job.company_name or 'N/A'} (Expired: {expiry})")
        if total_expired > 10:
            print(f"   ... and {total_expired - 10} more")
        
        print("\n🗑️  Removing related data...")
        
        # Delete related similarity scores
        similarity_count = session.query(SimilarityScore).filter(
            SimilarityScore.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        print(f"   • Deleted {similarity_count} similarity scores")
        
        # Delete related email notifications
        email_count = session.query(EmailNotification).filter(
            EmailNotification.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        print(f"   • Deleted {email_count} email notifications")
        
        # Delete related job vectors
        vector_count = session.query(JobVector).filter(
            JobVector.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        print(f"   • Deleted {vector_count} job vectors")
        
        # Delete the expired jobs
        session.query(Opportunity).filter(
            Opportunity.id.in_(expired_job_ids)
        ).delete(synchronize_session=False)
        print(f"   • Deleted {total_expired} expired jobs")
        
        # Commit all deletions
        session.commit()
        
        print("\n" + "=" * 60)
        print(f"✅ Cleanup completed successfully!")
        print(f"   Total expired jobs removed: {total_expired}")
        print(f"   Total records deleted: {similarity_count + email_count + vector_count + total_expired}")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        session.close()


def get_expiry_stats():
    """
    Get statistics about job expiry
    """
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        now = datetime.now()
        
        # Total jobs
        total = session.query(Opportunity).count()
        
        # Active jobs
        active = session.query(Opportunity).filter(
            (Opportunity.application_end_date > now) | 
            (Opportunity.application_end_date == None)
        ).count()
        
        # Expired jobs
        expired = session.query(Opportunity).filter(
            (Opportunity.application_end_date < now) & 
            (Opportunity.application_end_date != None)
        ).count()
        
        # Jobs with no end date
        no_end_date = session.query(Opportunity).filter(
            Opportunity.application_end_date == None
        ).count()
        
        print("\n📊 Job Expiry Statistics")
        print("=" * 60)
        print(f"Total jobs in database:     {total}")
        print(f"Active jobs (not expired):  {active} ({(active/total*100):.1f}%)")
        print(f"Expired jobs:               {expired} ({(expired/total*100):.1f}%)")
        print(f"Jobs with no end date:      {no_end_date} ({(no_end_date/total*100):.1f}%)")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error getting stats: {str(e)}")
        
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    # Show stats
    get_expiry_stats()
    
    print("\n")
    
    # Ask for confirmation if running cleanup
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        response = input("\n⚠️  This will DELETE all expired jobs and their related data!\nConfirm? (yes/no): ")
        if response.lower() == "yes":
            cleanup_expired_jobs()
        else:
            print("Cleanup cancelled.")
    else:
        print("\n💡 To clean up expired jobs, run:")
        print("   python cleanup_expired_jobs.py --cleanup")
