"""
Run from backend folder:
python check_scores.py
"""
import sys
sys.path.insert(0, '.')

import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.database import SessionLocal
from app.models import User, ResumeVector, JobVector, Opportunity

db = SessionLocal()

# Check users
users = db.query(User).filter(User.resume_text != None).all()
print(f"Users with resume text: {len(users)}")
for u in users:
    print(f"  User {u.user_id}: {u.name} | resume_text length: {len(u.resume_text or '')}")

# Check vectors exist
resume_vecs = db.query(ResumeVector).all()
job_vecs = db.query(JobVector).all()
print(f"\nResume vectors in DB: {len(resume_vecs)}")
print(f"Job vectors in DB:    {len(job_vecs)}")

if not resume_vecs or not job_vecs:
    print("ERROR: Missing vectors!")
    db.close()
    sys.exit()

# Check dimensions
rv = np.array(json.loads(resume_vecs[0].vector_data))
jv = np.array(json.loads(job_vecs[0].vector_data))
print(f"\nResume vector shape: {rv.shape}")
print(f"Job vector shape:    {jv.shape}")

# Compute top 10 scores for first user
print(f"\nTop 10 similarity scores for User {resume_vecs[0].user_id}:")
scores = []
for jv_row in job_vecs:
    jv_arr = np.array(json.loads(jv_row.vector_data))
    score = cosine_similarity([rv], [jv_arr])[0][0]
    scores.append((jv_row.job_id, score))

scores.sort(key=lambda x: x[1], reverse=True)
for job_id, score in scores[:10]:
    job = db.query(Opportunity).filter(Opportunity.id == job_id).first()
    print(f"  Score: {score:.4f} | {job.role} at {job.company_name}")

print(f"\nHighest score: {scores[0][1]:.4f}")
print(f"Scores above 0.75: {sum(1 for _, s in scores if s >= 0.75)}")
print(f"Scores above 0.50: {sum(1 for _, s in scores if s >= 0.50)}")
print(f"Scores above 0.30: {sum(1 for _, s in scores if s >= 0.30)}")

db.close()