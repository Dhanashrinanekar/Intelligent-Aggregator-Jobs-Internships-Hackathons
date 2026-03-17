"""Resume Upload and Processing Routes"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.auth import get_current_user
from app.models import User, ResumeVector
from app.services.resume_parser import ResumeParser
from app.services.vectorizer import VectorizerService
from app.services.matcher import MatcherService
import os
import shutil
import json
from datetime import datetime

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
        
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")
        
        # Validate file size (5MB limit)
        contents = await file.read()
        file_size = len(contents)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
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
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        print(f"✅ File saved: {file_path}")
        
        # Extract text from resume
        parser = ResumeParser()
        try:
            resume_text = parser.extract_text(file_path)
            
            if not resume_text or len(resume_text.strip()) < 50:
                raise ValueError("Could not extract meaningful text from resume")
            
            print(f"✅ Text extracted: {len(resume_text)} characters")
            
        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            # Clean up file
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=400, 
                detail=f"Could not process resume file. Please ensure it's a valid PDF or DOCX. Error: {str(e)}"
            )
        
        # Extract skills
        skills = parser.extract_skills(resume_text)
        print(f"✅ Skills extracted: {skills}")
        
        # Update user record
        current_user.resume_file = file_path
        current_user.resume_text = resume_text
        current_user.skills = ", ".join(skills) if skills else None
        
        # Generate TF-IDF vector
        try:
            vectorizer = VectorizerService()
            # Prepare text for vectorization
            vector_text = resume_text
            if skills:
                vector_text += " " + " ".join(skills)
            
            # Fit and transform
            vector = vectorizer.fit_transform_corpus([vector_text])[0]
            print(f"✅ Vector generated: shape {vector.shape}")
            
            # Save/update vector in database
            existing_vector = db.query(ResumeVector).filter(
                ResumeVector.user_id == current_user.user_id
            ).first()
            
            vector_json = json.dumps(vector.tolist())
            
            if existing_vector:
                existing_vector.vector_data = vector_json
                print("✅ Updated existing vector")
            else:
                resume_vector = ResumeVector(
                    user_id=current_user.user_id,
                    vector_data=vector_json
                )
                db.add(resume_vector)
                print("✅ Created new vector")
            
            db.commit()
            
        except Exception as e:
            print(f"❌ Error generating vector: {e}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error processing resume: {str(e)}"
            )
        
        # Match with jobs
        matches_count = 0
        try:
            matcher = MatcherService(db)
            matches = matcher.match_user_with_jobs(current_user.user_id, threshold=0.75)
            matches_count = len(matches)
            print(f"✅ Found {matches_count} job matches")
        except Exception as e:
            print(f"⚠️  Warning: Could not generate matches: {e}")
            # Don't fail the upload if matching fails
            matches_count = 0
        
        return {
            "message": "Resume uploaded successfully",
            "skills_extracted": skills if skills else [],
            "matches_found": matches_count,
            "resume_file": safe_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in upload_resume: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )