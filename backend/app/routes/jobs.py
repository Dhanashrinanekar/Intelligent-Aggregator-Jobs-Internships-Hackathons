"""Job Search and Browse Routes"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Opportunity
from app.schemas import JobResponse

router = APIRouter()

@router.get("/search", response_model=dict)
async def search_jobs(
    keyword: Optional[str] = None,
    opportunity_type: Optional[str] = None,
    portal: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search jobs with filters - PUBLIC endpoint (no authentication required)
    Only returns active jobs (not expired)
    
    Query Parameters:
    - keyword: Search in role, skills, or company name
    - opportunity_type: Filter by job type (job/internship)
    - portal: Filter by job portal (Indeed/Naukri/Jooble)
    - page: Page number (default: 1)
    - limit: Results per page (default: 20, max: 100)
    """
    try:
        query = db.query(Opportunity)
        
        # Filter out expired jobs - only show jobs where end date is in future or null
        now = datetime.now()
        query = query.filter(
            (Opportunity.application_end_date > now) | 
            (Opportunity.application_end_date == None)
        )
        
        # Apply filters
        if keyword:
            keyword_filter = f"%{keyword}%"
            query = query.filter(
                or_(
                    Opportunity.role.ilike(keyword_filter),
                    Opportunity.skills.ilike(keyword_filter),
                    Opportunity.company_name.ilike(keyword_filter)
                )
            )
        
        if opportunity_type:
            query = query.filter(Opportunity.opportunity_type.ilike(f"%{opportunity_type}%"))
        
        if portal:
            query = query.filter(Opportunity.job_portal_name.ilike(f"%{portal}%"))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        jobs = query.order_by(Opportunity.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to response format
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                "id": job.id,
                "company_name": job.company_name or "Not specified",
                "role": job.role or "Not specified",
                "opportunity_type": job.opportunity_type or "job",
                "skills": job.skills or "Not specified",
                "experience_required": job.experience_required or "Not specified",
                "job_portal_name": job.job_portal_name or "Other",
                "application_link": job.application_link or "#",
                "created_at": job.created_at.isoformat() if job.created_at else datetime.now().isoformat()
            })
        
        # Calculate total pages
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        
        return {
            "jobs": jobs_data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except Exception as e:
        print(f"Error in search_jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching jobs: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_details(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single job details by ID - PUBLIC endpoint
    Returns error if job is expired
    
    Parameters:
    - job_id: The ID of the job to retrieve
    """
    try:
        # Check if job is not expired
        now = datetime.now()
        job = db.query(Opportunity).filter(
            Opportunity.id == job_id,
            (Opportunity.application_end_date > now) | 
            (Opportunity.application_end_date == None)
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {job_id} not found or has expired"
            )
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_job_details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving job details: {str(e)}"
        )


@router.get("/portals/list")
async def get_portals(db: Session = Depends(get_db)):
    """
    Get list of all active job portals - PUBLIC endpoint
    Only returns portals that have non-expired jobs
    
    Returns list of unique portal names from database
    """
    try:
        now = datetime.now()
        portals = db.query(Opportunity.job_portal_name).filter(
            (Opportunity.application_end_date > now) | 
            (Opportunity.application_end_date == None)
        ).distinct().all()
        portal_list = [p[0] for p in portals if p[0]]
        
        return {
            "portals": portal_list,
            "count": len(portal_list)
        }
        
    except Exception as e:
        print(f"Error in get_portals: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving portals: {str(e)}"
        )


@router.get("/stats/summary")
async def get_job_stats(db: Session = Depends(get_db)):
    """
    Get job statistics - PUBLIC endpoint
    Only counts active (non-expired) jobs
    
    Returns statistics about available jobs
    """
    try:
        now = datetime.now()
        
        # Build base query for active jobs only
        base_query = db.query(Opportunity).filter(
            (Opportunity.application_end_date > now) | 
            (Opportunity.application_end_date == None)
        )
        
        # Total jobs
        total_jobs = base_query.count()
        
        # Jobs by type
        job_types = base_query.with_entities(
            Opportunity.opportunity_type,
            db.func.count(Opportunity.id)
        ).group_by(Opportunity.opportunity_type).all()
        
        types_dict = {job_type: count for job_type, count in job_types if job_type}
        
        # Jobs by portal
        portals = base_query.with_entities(
            Opportunity.job_portal_name,
            db.func.count(Opportunity.id)
        ).group_by(Opportunity.job_portal_name).all()
        
        portals_dict = {portal: count for portal, count in portals if portal}
        
        return {
            "total_jobs": total_jobs,
            "by_type": types_dict,
            "by_portal": portals_dict,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error in get_job_stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )