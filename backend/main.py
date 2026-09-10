import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import settings
from .database import Base, SessionLocal, engine, ensure_db_schema
from .routers import admin, auth, curriculum, evidence, lessons, parent, reports, student, voice

logger = logging.getLogger(__name__)
MIGRATION_HEAD = "0009_admin_profiles"

if not settings.is_production and settings.AUTO_INIT_DB:
    Base.metadata.create_all(bind=engine)
    ensure_db_schema()
    from .seed_data import seed
    seed(include_demo=settings.SEED_MODE.lower() == "demo")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION,
              description="Backend API for HomeWiseEdu AI-powered structured homeschooling platform.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Cache-Control"],
)
app.mount("/uploads/audio", StaticFiles(directory=settings.TTS_CACHE_DIR), name="audio")

for router in (auth.router, curriculum.router, lessons.router, evidence.router, parent.router,
               student.router, admin.router, voice.router, reports.router):
    app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.error("Unhandled request failure method=%s path=%s type=%s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "An internal service error occurred"})


@app.get("/")
def root():
    return {"app": settings.PROJECT_NAME, "status": "online", "principle": "Structured curriculum FIRST, AI support SECOND."}


@app.get("/health")
def health_check():
    return {"status": "alive"}


@app.get("/ready")
def readiness_check():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            if settings.is_production:
                revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
                if revision != MIGRATION_HEAD:
                    return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "database migration required"})
    except Exception as exc:
        logger.warning("Readiness check failed type=%s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "database unavailable"})
    return {"status": "ready"}
