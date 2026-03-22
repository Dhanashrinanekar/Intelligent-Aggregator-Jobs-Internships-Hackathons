"""
Run this from inside your backend folder:
python fix_and_email.py
"""
import json
import sys

sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User, Opportunity, ResumeVector, JobVector, SimilarityScore
from app.services.vectorizer import VectorizerService
from app.services.email_service import EmailService

THRESHOLD = 0.3

db = SessionLocal()

# Step 1: Clear old vectors and scores
print("Step 1: Clearing old vectors...")
db.query(SimilarityScore).delete()
db.query(ResumeVector).delete()
db.query(JobVector).delete()
db.commit()
print("  Done.")

# Step 2: Get all users and jobs
users = db.query(User).filter(User.resume_text != None).all()
jobs = db.query(Opportunity).all()
print(f"Step 2: Found {len(users)} users with resumes, {len(jobs)} jobs")

if len(users) == 0:
    print("  ERROR: No users have resume text. Please upload a resume first!")
    db.close()
    sys.exit()

if len(jobs) == 0:
    print("  ERROR: No jobs in database. Please run the scrapers first!")
    db.close()
    sys.exit()

# Step 3: Build ONE corpus of all texts together
print("Step 3: Building combined text corpus...")
vectorizer = VectorizerService()
all_texts = []

for user in users:
    all_texts.append(user.resume_text or '')

for job in jobs:
    text = vectorizer.prepare_text(
        role=job.role or '',
        skills=job.skills or '',
        company=job.company_name or ''
    )
    all_texts.append(text)

# Step 4: Fit ONE vectorizer on ALL texts
print("Step 4: Fitting vectorizer on all texts...")
vectors = vectorizer.fit_transform_corpus(all_texts)
print(f"  Vector dimensions: {vectors.shape[1]}")

# Step 5: Save user resume vectors
print("Step 5: Saving user vectors...")
for i, user in enumerate(users):
    rv = ResumeVector(
        user_id=user.user_id,
        vector_data=json.dumps(vectors[i].tolist())
    )
    db.add(rv)

# Step 6: Save job vectors
print("Step 6: Saving job vectors...")
for i, job in enumerate(jobs):
    jv = JobVector(
        job_id=job.id,
        vector_data=json.dumps(vectors[len(users) + i].tolist())
    )
    db.add(jv)

db.commit()
print("  Vectors saved successfully.")

# Step 7: Run matching
print("Step 7: Running matching...")
from app.services.matcher import MatcherService
matcher = MatcherService(db)
matcher.match_all_users_with_new_jobs(threshold=THRESHOLD)
print("  Matching done.")

# Step 8: Send emails
print("Step 8: Sending emails...")
email_service = EmailService()
email_service.send_job_match_notification(db)

db.close()
print("\nAll done! Check your inbox.")