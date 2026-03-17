
"""
FastAPI Main Application
Complete AI Job Aggregator Backend
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import os

from app.database import Base, engine
from app.routes import users, jobs, resume, recommendations
from app.scheduler.tasks import start_scheduler

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="AI Job Aggregator API",
    description="AI-powered job matching with resume analysis and email notifications",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])

# Serve frontend pages
@app.get("/", response_class=HTMLResponse)
async def home_page():
    """Serve home page"""
    file_path = frontend_path / "index.html"
    if file_path.exists():
        return FileResponse(file_path)
    return {"message": "AI Job Aggregator API", "docs": "/api/docs"}

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return FileResponse(frontend_path / "register.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return FileResponse(frontend_path / "login.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return FileResponse(frontend_path / "dashboard.html")

@app.get("/upload-resume", response_class=HTMLResponse)
async def upload_resume_page():
    return FileResponse(frontend_path / "upload-resume.html")

@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page():
    return FileResponse(frontend_path / "jobs.html")

@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page():
    return FileResponse(frontend_path / "recommendations.html")

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background scheduler on startup"""
    start_scheduler()
    print("✅ Application started successfully")

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)