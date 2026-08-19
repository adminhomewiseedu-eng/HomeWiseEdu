import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base
from .seed_data import seed

# Import all API routers
from .routers import auth, curriculum, lessons, evidence, parent, student, admin, voice, reports

# Ensure database tables are created & seeded
Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend API for HomeWiseEdu AI-powered structured homeschooling platform."
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API routers
app.include_router(auth.router)
app.include_router(curriculum.router)
app.include_router(lessons.router)
app.include_router(evidence.router)
app.include_router(parent.router)
app.include_router(student.router)
app.include_router(admin.router)
app.include_router(voice.router)
app.include_router(reports.router)

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "principle": "Structured curriculum FIRST, AI support SECOND."
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
