"""Job Recommendations Routes"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, SimilarityScore, Opportunity
from app.auth.auth import get_current_user
from app.services.matcher import MatcherService

router = APIRouter()

@router.get("/")
async def get_recommendations(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized job recommendations"""
    try:
        # Check if user has uploaded resume
        if not current_user.resume_text:
            return {
                "recommendations": [],
                "message": "Please upload your resume first to get recommendations",
                "total": 0
            }
        
        # Get recommendations from database
        recommendations = db.query(
            SimilarityScore, Opportunity
        ).join(
            Opportunity, SimilarityScore.job_id == Opportunity.id
        ).filter(
            SimilarityScore.user_id == current_user.user_id,
            SimilarityScore.similarity_score >= 0.75
        ).order_by(
            SimilarityScore.similarity_score.desc()
        ).limit(limit).all()
        
        # Format response
        result = []
        for score, job in recommendations:
            result.append({
                "job_id": job.id,
                "company_name": job.company_name or "Not specified",
                "role": job.role or "Not specified",
                "opportunity_type": job.opportunity_type or "job",
                "skills": job.skills or "Not specified",
                "similarity_score": float(score.similarity_score),
                "rank_position": score.rank_position or 0,
                "application_link": job.application_link or "#"
            })
        
        return result
        
    except Exception as e:
        print(f"❌ Error in get_recommendations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error loading recommendations: {str(e)}"
        )


@router.post("/regenerate")
async def regenerate_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate recommendations for current user"""
    try:
        if not current_user.resume_text:
            raise HTTPException(
                status_code=400,
                detail="Please upload your resume first"
            )
        
        # Run matching
        matcher = MatcherService(db)
        matches = matcher.match_user_with_jobs(current_user.user_id, threshold=0.75)
        
        return {
            "message": "Recommendations regenerated successfully",
            "matches_found": len(matches)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in regenerate_recommendations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating recommendations: {str(e)}"
        )