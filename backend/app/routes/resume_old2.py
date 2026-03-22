"""Resume Upload and Processing Routes - Simplified"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.auth import get_current_user
from app.models import User, Opportunity, SimilarityScore
from app.services.resume_parser import ResumeParser
import os
import json
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

router = APIRouter()

@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process resume"""
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith('.pdf') or filename_lower.endswith('.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")
        
        # Read file contents
        contents = await file.read()
        file_size = len(contents)
        
        # Validate file size (5MB limit)
        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Create upload directory
        upload_dir = "uploads/resumes"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"user_{current_user.user_id}_{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        print(f"✅ File saved: {file_path}")
        
        # Extract text from resume
        parser = ResumeParser()
        resume_text = parser.extract_text(file_path)
        
        if not resume_text or len(resume_text.strip()) < 50:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail="Could not extract text from resume. Please ensure it's a valid PDF or DOCX file.")
        
        print(f"✅ Text extracted: {len(resume_text)} characters")
        
        # Extract skills
        skills = parser.extract_skills(resume_text)
        print(f"✅ Skills extracted: {len(skills)} skills found")
        
        # Update user record
        current_user.resume_file = file_path
        current_user.resume_text = resume_text
        current_user.skills = ", ".join(skills) if skills else None
        db.commit()
        print("✅ User record updated")
        
        # Job matching
        matches_count = 0
        try:
            # Get all jobs from database
            all_jobs = db.query(Opportunity).all()
            print(f"ℹ️  Total jobs in database: {len(all_jobs)}")
            
            if len(all_jobs) > 0:
                # Prepare texts for vectorization
                resume_text_lower = resume_text.lower()
                skills_text = " ".join(skills).lower() if skills else ""
                resume_combined = resume_text_lower + " " + skills_text
                
                job_texts = []
                for job in all_jobs:
                    role = (job.role or "").lower()
                    skills_req = (job.skills or "").lower()
                    company = (job.company_name or "").lower()
                    job_combined = f"{role} {skills_req} {company}"
                    job_texts.append(job_combined)
                
                # Vectorize all texts together
                all_texts = [resume_combined] + job_texts
                
                vectorizer = TfidfVectorizer(
                    max_features=300,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=1
                )
                
                vectors = vectorizer.fit_transform(all_texts)
                vectors_dense = vectors.toarray()  # Convert sparse matrix to dense array
                resume_vector = vectors_dense[0]
                
                # Calculate similarity for each job
                for idx, job in enumerate(all_jobs):
                    job_vector = vectors_dense[idx + 1]
                    similarity = float(cosine_similarity([resume_vector], [job_vector])[0][0])
                    
                    # Save high-similarity matches
                    if similarity >= 0.25:
                        existing = db.query(SimilarityScore).filter(
                            SimilarityScore.user_id == current_user.user_id,
                            SimilarityScore.job_id == job.id
                        ).first()
                        
                        if existing:
                            existing.similarity_score = similarity
                        else:
                            new_score = SimilarityScore(
                                user_id=current_user.user_id,
                                job_id=job.id,
                                similarity_score=similarity
                            )
                            db.add(new_score)
                        
                        matches_count += 1
                
                db.commit()
                print(f"✅ Job matching complete: {matches_count} matches found")
            else:
                print("ℹ️  No jobs in database yet")
                
        except Exception as e:
            print(f"⚠️  Warning in matching: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Return success response
        return {
            "message": "Resume uploaded and processed successfully!",
            "skills_extracted": skills if skills else [],
            "matches_found": matches_count,
            "resume_file": safe_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in upload_resume: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume: {str(e)}"
        )
