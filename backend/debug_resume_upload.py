#!/usr/bin/env python3
"""
Debug script to test resume upload endpoint directly
This helps identify the exact error
"""
import sys
import os
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User, Opportunity
from app.services.resume_parser import ResumeParser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

print("🧪 Testing Resume Upload Logic...")
print("=" * 70)

# Step 1: Check database
print("\n1️⃣  Checking database...")
try:
    db = SessionLocal()
    user_count = db.query(User).count()
    job_count = db.query(Opportunity).count()
    print(f"   ✅ Users: {user_count}")
    print(f"   ✅ Jobs: {job_count}")
    
    if job_count == 0:
        print("   ⚠️  No jobs in database - upload will have 0 matches (normal)")
    
    db.close()
except Exception as e:
    print(f"   ❌ Database error: {e}")
    sys.exit(1)

# Step 2: Create sample resume text
print("\n2️⃣  Creating sample resume...")
sample_resume = """
Education:
Bachelor of Science in Computer Science from University of Technology
Graduation: May 2023

Skills:
- Python, JavaScript, Java
- Django, FastAPI, React
- PostgreSQL, MongoDB
- AWS, Docker, Kubernetes
- Machine Learning, NLP
- Git, GitHub

Experience:
Senior Software Engineer at Tech Company (2022 - Present)
- Developed full-stack web applications using Python and React
- Led team of 5 developers
- Implemented machine learning models for data analysis
- Managed AWS infrastructure and deployment

Junior Developer at StartUp Inc (2020 - 2022)
- Built REST APIs using FastAPI
- Worked with PostgreSQL and MongoDB databases
- Implemented CI/CD pipelines using GitHub Actions
"""

print(f"   ✅ Sample resume: {len(sample_resume)} characters")

# Step 3: Test skill extraction
print("\n3️⃣  Testing skill extraction...")
try:
    parser = ResumeParser()
    skills = parser.extract_skills(sample_resume)
    print(f"   ✅ Skills extracted: {skills}")
except Exception as e:
    print(f"   ❌ Skill extraction error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test matching logic
print("\n4️⃣  Testing matching logic...")
try:
    db = SessionLocal()
    all_jobs = db.query(Opportunity).all()
    
    if len(all_jobs) > 0:
        print(f"   ℹ️  Testing with {min(10, len(all_jobs))} sample jobs...")
        
        # Take first 10 jobs for testing
        test_jobs = all_jobs[:10]
        
        # Prepare texts
        resume_text_lower = sample_resume.lower()
        skills_text = " ".join(skills).lower() if skills else ""
        resume_combined = resume_text_lower + " " + skills_text
        
        job_texts = []
        for job in test_jobs:
            role = (job.role or "").lower()
            skills_req = (job.skills or "").lower()
            company = (job.company_name or "").lower()
            job_combined = f"{role} {skills_req} {company}"
            job_texts.append(job_combined)
        
        print(f"   ✅ Prepared {len(job_texts)} job texts")
        
        # Vectorize
        all_texts = [resume_combined] + job_texts
        print(f"   ℹ️  Vectorizing {len(all_texts)} texts...")
        
        vectorizer = TfidfVectorizer(
            max_features=300,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        
        vectors = vectorizer.fit_transform(all_texts)
        print(f"   ✅ Vectorizer created vectors shape: {vectors.shape}")
        print(f"   ℹ️  Vector type: {type(vectors)}")
        
        # Convert to dense
        vectors_dense = vectors.toarray()
        print(f"   ✅ Converted to dense array shape: {vectors_dense.shape}")
        
        resume_vector = vectors_dense[0]
        print(f"   ✅ Resume vector shape: {resume_vector.shape}")
        
        # Calculate similarities
        matches = 0
        for idx, job in enumerate(test_jobs):
            job_vector = vectors_dense[idx + 1]
            similarity = float(cosine_similarity([resume_vector], [job_vector])[0][0])
            
            if similarity >= 0.25:
                matches += 1
                print(f"      • Job {job.id} ({job.role}): {similarity:.2%} match")
        
        print(f"   ✅ Matching complete: {matches} matches found!")
    else:
        print("   ℹ️  No jobs in database - skipping match test")
    
    db.close()
    
except Exception as e:
    print(f"   ❌ Matching error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ All tests passed!")
print("=" * 70)
