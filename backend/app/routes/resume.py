"""Resume Upload and Processing Routes - Improved Error Handling"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.auth import get_current_user
from app.models import User, Opportunity, SimilarityScore
from app.services.resume_parser import ResumeParser
import os
import json
import traceback
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
    upload_error = None
    
    try:
        print("\n" + "="*70)
        print("📁 RESUME UPLOAD STARTED")
        print("="*70)
        
        # Validate file type
        if not file.filename:
            print("❌ No file provided")
            raise HTTPException(status_code=400, detail="No file selected")
        
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith('.pdf') or filename_lower.endswith('.docx')):
            print(f"❌ Invalid file type: {filename_lower}")
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")
        
        # Read file contents
        print(f"📂 Reading file: {file.filename}")
        contents = await file.read()
        file_size = len(contents)
        print(f"✅ File size: {file_size / 1024:.2f} KB")
        
        # Validate file size (5MB limit)
        if file_size > 5 * 1024 * 1024:
            print("❌ File too large")
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
        
        if file_size == 0:
            print("❌ Empty file")
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Create upload directory
        upload_dir = "uploads/resumes"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"user_{current_user.user_id}_{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Save file to disk
        print(f"💾 Saving to: {file_path}")
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        print("✅ File saved")
        
        # Extract text from resume
        print("📖 Extracting text...")
        parser = ResumeParser()
        resume_text = parser.extract_text(file_path)
        
        if not resume_text or len(resume_text.strip()) < 50:
            print("❌ Could not extract meaningful text")
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail="Could not extract text from resume. Please ensure it's a valid PDF or DOCX file.")
        
        print(f"✅ Text extracted: {len(resume_text)} characters")
        
        # Extract skills
        print("🎯 Extracting skills...")
        skills = parser.extract_skills(resume_text)
        print(f"✅ Skills found: {skills}")
        
        # Update user record
        print("👤 Updating user record...")
        current_user.resume_file = safe_filename
        current_user.resume_text = resume_text
        current_user.skills = ", ".join(skills) if skills else None
        db.commit()
        print("✅ User record updated")
        
        # Job matching
        matches_count = 0
        print("🔍 Starting job matching...")
        
        try:
            # Get all jobs from database
            all_jobs = db.query(Opportunity).all()
            print(f"📊 Total jobs in database: {len(all_jobs)}")
            
            if len(all_jobs) > 0:
                print("🚀 Processing matches...")
                
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
                
                print(f"✅ Prepared {len(job_texts)} job descriptions")
                
                # Vectorize all texts together
                all_texts = [resume_combined] + job_texts
                print(f"🔢 Vectorizing {len(all_texts)} texts...")
                
                vectorizer = TfidfVectorizer(
                    max_features=300,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=1
                )
                
                vectors = vectorizer.fit_transform(all_texts)
                print(f"✅ Vectorizer output shape: {vectors.shape}")
                
                # Convert sparse matrix to dense
                vectors_dense = vectors.toarray()
                print(f"✅ Converted to dense: {vectors_dense.shape}")
                
                resume_vector = vectors_dense[0]
                print(f"✅ Resume vector extracted: {resume_vector.shape}")
                
                # Calculate similarity for each job
                print("⚙️  Calculating similarities...")
                matches_list = []
                for idx, job in enumerate(all_jobs):
                    try:
                        job_vector = vectors_dense[idx + 1]
                        sim_result = cosine_similarity([resume_vector], [job_vector])
                        similarity = float(sim_result[0][0])
                        
                        if similarity >= 0.25:
                            matches_list.append({
                                'job_id': job.id,
                                'similarity': similarity
                            })
                            
                            # Save to database
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
                    except Exception as job_err:
                        print(f"⚠️  Error processing job {idx}: {str(job_err)}")
                        # Continue to next job
                        continue
                
                db.commit()
                matches_count = len(matches_list)
                print(f"✅ Matching complete!")
                print(f"✅ Found {matches_count} job matches")
                
            else:
                print("ℹ️  No jobs in database yet")
                
        except Exception as matching_err:
            print(f"⚠️  Error during matching phase: {str(matching_err)}")
            traceback.print_exc()
            # Don't stop upload if matching fails - it's not critical
            matches_count = 0
        
        # Build response
        print(f"\n📊 FINAL RESULTS:")
        print(f"   • Skills extracted: {len(skills)}")
        print(f"   • Job matches found: {matches_count}")
        print(f"   • Resume saved as: {safe_filename}")
        
        response_data = {
            "message": "Resume uploaded and processed successfully!",
            "skills_extracted": skills if skills else [],
            "matches_found": matches_count,
            "resume_file": safe_filename
        }
        
        print("\n✅ UPLOAD SUCCESSFUL")
        print("="*70 + "\n")
        
        return response_data
        
    except HTTPException as http_err:
        print(f"\n❌ HTTP Error: {http_err.detail}")
        print("="*70 + "\n")
        raise

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ UPLOAD FAILED - Unexpected error: {error_msg}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        print("="*70 + "\n")

        # Return JSON error response
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Error processing resume: {error_msg}",
                "error_type": type(e).__name__
            }
        )


@router.get('/download')
async def download_resume(
    current_user: User = Depends(get_current_user)
):
    """Download the current user's uploaded resume."""
    if not current_user.resume_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No resume uploaded")

    resume_filename = os.path.basename(current_user.resume_file)
    resume_path = current_user.resume_file

    if not os.path.isabs(resume_path):
        resume_path = os.path.join('uploads', 'resumes', resume_filename)

    if not os.path.exists(resume_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file not found")

    return FileResponse(path=resume_path, filename=resume_filename, media_type='application/octet-stream')
