from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..database import get_db
from ..models import Subject, Unit, Lesson, LessonDay, QuizQuestion
from ..schemas import SubjectOut, LessonDetailOut
from ..services.curriculum_importer import import_curriculum_csv_data

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])

@router.get("/subjects", response_model=List[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.id.asc()).all()

@router.get("/lessons/{lesson_id}", response_model=LessonDetailOut)
def get_lesson_detail(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

@router.post("/import-csv")
async def import_curriculum_csv(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Imports a curriculum blueprint CSV file idempotently into the database."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV (.csv)")
    
    contents = await file.read()
    csv_text = contents.decode("utf-8-sig", errors="ignore")
    
    try:
        stats = import_curriculum_csv_data(csv_text, db)
        return {
            "message": "Curriculum CSV successfully imported",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import curriculum CSV: {str(e)}")
