from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..database import get_db
from ..models import Subject, Unit, Lesson, LessonDay, QuizQuestion
from ..schemas import SubjectOut, LessonDetailOut, LessonDayOut
from ..models import User
from .auth import get_current_user, require_admin
from ..services.curriculum_importer import import_curriculum_csv_data
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])

PUBLISHED_STATUSES = {"active", "published"}


class PublishLessonRequest(BaseModel):
    publish: bool = True


class LessonDayUpdate(BaseModel):
    title: Optional[str] = None
    activity_type: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    key_concept: Optional[str] = None
    ai_script: Optional[str] = None
    real_world_context: Optional[str] = None
    visual_support: Optional[str] = None
    practice_questions: Optional[List[Any]] = None
    vocabulary: Optional[List[Any]] = None

@router.get("/subjects", response_model=List[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.id.asc()).all()

@router.get("/lessons/{lesson_id}", response_model=LessonDetailOut)
def get_lesson_detail(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if current_user.role != "admin" and lesson.days and not any((day.status or "").lower() in PUBLISHED_STATUSES for day in lesson.days):
        raise HTTPException(status_code=404, detail="Lesson not found")
    # Quiz questions (and their answers) are available only through the
    # readiness-gated lesson quiz endpoint.
    return LessonDetailOut.model_validate(lesson).model_copy(update={"quiz_questions": []})

@router.post("/import-csv")
async def import_curriculum_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Imports a curriculum blueprint CSV file idempotently into the database."""
    if not (file.filename or "").lower().endswith(".csv") or file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        raise HTTPException(status_code=400, detail="File must be a CSV (.csv)")
    
    contents = await file.read(5 * 1024 * 1024 + 1)
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Curriculum CSV exceeds the 5 MB limit")
    try:
        csv_text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Curriculum CSV must use UTF-8 encoding") from exc
    
    try:
        stats = import_curriculum_csv_data(csv_text, db)
        db.commit()
        return {
            "message": "Curriculum CSV successfully imported",
            "stats": stats
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Curriculum import failed")
        raise HTTPException(status_code=500, detail="Curriculum import failed safely; no rows were applied") from exc


@router.post("/import-csv/validate")
async def validate_curriculum_csv(file: UploadFile = File(...), db: Session = Depends(get_db),
                                  current_user: User = Depends(require_admin)):
    if not (file.filename or "").lower().endswith(".csv") or file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        raise HTTPException(status_code=400, detail="File must be a CSV (.csv)")
    contents = await file.read(5 * 1024 * 1024 + 1)
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Curriculum CSV exceeds the 5 MB limit")
    try:
        stats = import_curriculum_csv_data(contents.decode("utf-8-sig"), db)
        db.rollback()
        return {"valid": True, "stats": stats, "message": "Validation passed. Import will keep lesson days pending."}
    except (UnicodeDecodeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/lessons")
def list_admin_lessons(response: Response, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    response.headers["Cache-Control"] = "no-store"
    lessons = db.query(Lesson).order_by(Lesson.level.asc(), Lesson.order_num.asc()).all()
    return [{
        "id": lesson.id, "title": lesson.title, "subtopic": lesson.topic, "lesson_number": lesson.order_num,
        "unit": lesson.unit.title, "subject": lesson.unit.subject.title, "level": lesson.level,
        "curriculum_country": lesson.curriculum_country,
        "status": "published" if lesson.days and all((d.status or "").lower() in PUBLISHED_STATUSES for d in lesson.days) else "pending",
        "days": len(lesson.days), "lesson_days": [{"id": day.id, "day_number": day.day_number,
            "activity_type": day.activity_type, "status": day.status} for day in lesson.days],
    } for lesson in lessons]


@router.patch("/admin/lessons/{lesson_id}/publication")
def set_lesson_publication(lesson_id: int, payload: PublishLessonRequest, db: Session = Depends(get_db),
                           current_user: User = Depends(require_admin)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if len(lesson.days) != 3:
        raise HTTPException(status_code=409, detail="A lesson must have exactly three days before publication")
    for day in lesson.days:
        day.status = "published" if payload.publish else "pending"
    db.commit()
    return {"lesson_id": lesson.id, "status": "published" if payload.publish else "pending"}


@router.patch("/admin/lesson-days/{day_id}", response_model=LessonDayOut)
def update_lesson_day(day_id: int, payload: LessonDayUpdate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_admin)):
    day = db.query(LessonDay).filter(LessonDay.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Lesson day not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(day, field, value)
    db.commit()
    db.refresh(day)
    return day
