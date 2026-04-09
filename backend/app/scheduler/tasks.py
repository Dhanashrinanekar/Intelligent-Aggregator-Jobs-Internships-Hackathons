"""Background Scheduled Tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.matcher import MatcherService
from app.services.email_service import EmailService
from app.services.vectorizer import VectorizerService
from app.models import Opportunity, JobVector, SimilarityScore, EmailNotification
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from backend/.env before any scraper checks them
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env')

# ─────────────────────────────────────────────────────────────────
# Keywords to scrape. Add / remove freely.
# ─────────────────────────────────────────────────────────────────
JOB_KEYWORDS = [
    "software engineer", "frontend developer", "backend developer",
    "full stack developer", "python developer", "java developer",
    "data engineer", "data analyst", "data scientist",
    "machine learning engineer", "AI engineer", "devops engineer",
    "cloud engineer", "mobile developer", "android developer",
    "ios developer", "react developer", "nodejs developer",
    "cybersecurity analyst", "QA engineer", "embedded engineer",
    "business analyst", "product manager", "financial analyst",
    "accountant", "marketing manager", "content writer",
    "hr manager", "sales executive", "operations manager",
    "ui ux designer", "graphic designer",
]

INTERNSHIP_KEYWORDS = [
    "software intern", "data science intern", "web development intern",
    "marketing intern", "business development intern",
    "machine learning intern", "ui ux intern", "finance intern",
    "hr intern", "content writing intern",
]

HACKATHON_KEYWORDS = [
    "hackathon", "coding competition", "datathon",
    "buildathon", "tech fest",
]


def _save_jobs_to_db(jobs: list, opportunity_type: str):
    """
    Save a list of job dicts using SQLAlchemy.
    opportunity_type must be: 'job', 'internship', or 'hackathon'

    Date fields are already resolved by each scraper via resolve_dates_for_job().
    Both application_start_date and application_end_date are guaranteed non-NULL.
    """
    if not jobs:
        return 0
    db = SessionLocal()
    inserted = 0
    try:
        for job in jobs:
            link = job.get("application_link")
            if not link or link == "N/A":
                continue
            if db.query(Opportunity).filter_by(application_link=link).first():
                continue
            db.add(Opportunity(
                company_name=job.get("company_name"),
                role=job.get("role"),
                opportunity_type=opportunity_type,
                skills=job.get("skills", "N/A"),
                experience_required=job.get("experience_required", "N/A"),
                job_portal_name=job.get("job_portal_name", "Unknown"),
                application_link=link,
                application_start_date=job.get("application_start_date"),
                application_end_date=job.get("application_end_date"),
            ))
            inserted += 1
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ DB save error: {e}")
    finally:
        db.close()
    return inserted


def fetch_new_jobs():
    """Fetch jobs, internships, and hackathons from all scrapers."""
    print(f"\n{'='*60}")
    print(f"🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting fetch_new_jobs...")
    print(f"{'='*60}")
    total_inserted = 0

    # ── 1. JOOBLE API ──
    try:
        api_key = os.getenv("JOOBLE_API_KEY")
        if not api_key:
            print("⚠️ JOOBLE_API_KEY not set — skipping Jooble")
        else:
            from app.scrapers.jooble_api import JoobleJobAggregator
            jooble = JoobleJobAggregator(api_key)

            for keyword in JOB_KEYWORDS[:10]:
                try:
                    results = jooble.search_jobs(keyword=keyword, location="India", num_pages=1, save_to_db=False)
                    n = _save_jobs_to_db(results, "job")
                    total_inserted += n
                    print(f"  ✅ Jooble job '{keyword}': {n} inserted")
                except Exception as e:
                    print(f"  ⚠️ Jooble job '{keyword}': {e}")

            for keyword in INTERNSHIP_KEYWORDS[:5]:
                try:
                    results = jooble.search_jobs(keyword=keyword, location="India", num_pages=1, save_to_db=False)
                    n = _save_jobs_to_db(results, "internship")
                    total_inserted += n
                    print(f"  ✅ Jooble internship '{keyword}': {n} inserted")
                except Exception as e:
                    print(f"  ⚠️ Jooble internship '{keyword}': {e}")

    except Exception as e:
        print(f"❌ Jooble failed entirely: {e}")

    # ── 2. NAUKRI ──
    try:
        from app.scrapers.naukri_scraper import scrape_naukri
        for keyword in JOB_KEYWORDS[:5]:
            try:
                results = scrape_naukri(keyword=keyword, num_pages=1, save_to_db=False)
                n = _save_jobs_to_db(results, "job")
                total_inserted += n
                print(f"  ✅ Naukri job '{keyword}': {n} inserted")
            except Exception as e:
                print(f"  ⚠️ Naukri job '{keyword}': {e}")
        for keyword in INTERNSHIP_KEYWORDS[:3]:
            try:
                results = scrape_naukri(keyword=keyword, num_pages=1, save_to_db=False)
                n = _save_jobs_to_db(results, "internship")
                total_inserted += n
                print(f"  ✅ Naukri internship '{keyword}': {n} inserted")
            except Exception as e:
                print(f"  ⚠️ Naukri internship '{keyword}': {e}")
    except Exception as e:
        print(f"❌ Naukri failed entirely: {e}")

    # ── 3. INDEED ──
    try:
        from app.scrapers.indeed_scraper import scrape_indeed
        for keyword in JOB_KEYWORDS[:5]:
            try:
                results = scrape_indeed(keyword=keyword, location="India", num_pages=1, save_to_db=False)
                n = _save_jobs_to_db(results, "job")
                total_inserted += n
                print(f"  ✅ Indeed job '{keyword}': {n} inserted")
            except Exception as e:
                print(f"  ⚠️ Indeed job '{keyword}': {e}")
        for keyword in INTERNSHIP_KEYWORDS[:3]:
            try:
                results = scrape_indeed(keyword=keyword, location="India", num_pages=1, save_to_db=False)
                n = _save_jobs_to_db(results, "internship")
                total_inserted += n
                print(f"  ✅ Indeed internship '{keyword}': {n} inserted")
            except Exception as e:
                print(f"  ⚠️ Indeed internship '{keyword}': {e}")
    except Exception as e:
        print(f"❌ Indeed failed entirely: {e}")

    # ── 4. UNSTOP ──
    try:
        from app.scrapers.unstop_scraper import scrape_unstop
        for cat, opp_type in [
            ("hackathons", "hackathon"),
            ("internships", "internship"),
            ("competitions", "competition"),
            ("jobs", "job")
        ]:
            try:
                results = scrape_unstop(keyword="", category=cat, num_pages=1, save_to_db=False)
                n = _save_jobs_to_db(results, opp_type)
                total_inserted += n
                print(f"  ✅ Unstop {cat}: {n} inserted")
            except Exception as e:
                print(f"  ⚠️ Unstop {cat}: {e}")
    except Exception as e:
        print(f"❌ Unstop failed entirely: {e}")

    print(f"\n✅ fetch_new_jobs complete — {total_inserted} total new opportunities inserted")
    print(f"{'='*60}\n")


def generate_job_vectors():
    """Generate TF-IDF vectors for new jobs"""
    db = SessionLocal()
    try:
        jobs_without_vectors = db.query(Opportunity).outerjoin(JobVector).filter(
            JobVector.job_vector_id == None
        ).all()

        if not jobs_without_vectors:
            print("No new jobs to vectorize")
            return

        vectorizer = VectorizerService()
        texts = []
        for job in jobs_without_vectors:
            text = vectorizer.prepare_text(
                role=job.role or "",
                skills=job.skills or "",
                company=job.company_name or ""
            )
            texts.append(text)

        vectors = vectorizer.fit_transform_corpus(texts)

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
    Remove all jobs whose application_end_date has passed.
    Also removes dependent rows from similarity_score, email_notifications, job_vector.
    Runs daily via the scheduler.

    Because every job now has a guaranteed non-NULL application_end_date
    (set by resolve_dates_for_job at scrape time), this query will always
    catch exactly the jobs that have truly expired.
    """
    db = SessionLocal()
    try:
        now = datetime.now()

        expired_jobs = db.query(Opportunity).filter(
            Opportunity.application_end_date != None,
            Opportunity.application_end_date < now
        ).all()

        if not expired_jobs:
            print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] No expired jobs to cleanup")
            return

        expired_job_ids = [job.id for job in expired_jobs]
        total_expired = len(expired_job_ids)
        print(f"\n🗑️  [{now.strftime('%Y-%m-%d %H:%M:%S')}] Cleaning up {total_expired} expired jobs...")

        # Delete dependent rows first
        sim_deleted = db.query(SimilarityScore).filter(
            SimilarityScore.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)

        email_deleted = db.query(EmailNotification).filter(
            EmailNotification.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)

        vec_deleted = db.query(JobVector).filter(
            JobVector.job_id.in_(expired_job_ids)
        ).delete(synchronize_session=False)

        # Delete the expired opportunities
        db.query(Opportunity).filter(
            Opportunity.id.in_(expired_job_ids)
        ).delete(synchronize_session=False)

        db.commit()

        print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] Cleanup complete!")
        print(f"   • Expired jobs removed:          {total_expired}")
        print(f"   • Similarity scores deleted:     {sim_deleted}")
        print(f"   • Email notifications deleted:   {email_deleted}")
        print(f"   • Job vectors deleted:           {vec_deleted}")

    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """Start background scheduler"""
    scheduler = BackgroundScheduler()

    # Fetch new jobs from all scrapers — runs immediately on startup, then every 6 hours
    scheduler.add_job(fetch_new_jobs, 'interval', hours=6, next_run_time=datetime.now())

    # Vectorize new jobs every hour
    scheduler.add_job(generate_job_vectors, 'interval', hours=1)

    # Match users and notify every 2 hours
    scheduler.add_job(match_and_notify, 'interval', hours=2)

    # Cleanup expired jobs daily
    scheduler.add_job(cleanup_expired_jobs, 'interval', hours=24)

    scheduler.start()
    print("✅ Scheduler started — fetch_new_jobs will run immediately and every 6 hours")