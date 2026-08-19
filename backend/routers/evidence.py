import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import LearningEvidence, Child, Lesson, LessonDay, StudentProgress, AIInteraction
from ..schemas import EvidenceOut
from ..services.openai_service import evaluate_student_work
from ..config import settings
from ..utils.levels import get_level_label

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

@router.post("/submit", response_model=EvidenceOut)
async def submit_evidence(
    child_id: int = Form(...),
    lesson_id: Optional[int] = Form(None),
    day_number: int = Form(1),
    subject: str = Form("Mathematics"),
    lesson_title: str = Form("Counting to 5"),
    skill: str = Form("Count up to 5 objects accurately"),
    evidence_type: str = Form("lesson"),
    submission_type: str = Form("text"),
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    saved_file_url = None
    file_name = None
    if file and file.filename:
        file_ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid.uuid4()}{file_ext}"
        dest_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_file_url = f"/uploads/{unique_name}"
        file_name = file.filename

    # Retrieve lesson context
    task_instructions = "Demonstrate your understanding and show your step-by-step working."
    level_num = child.level if child.level is not None else 0
    edu_sys = child.education_system or "UK"
    level_label = get_level_label(level_num, edu_sys)
    objectives = [skill]

    if lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if lesson:
            if lesson.default_evidence_task:
                task_instructions = lesson.default_evidence_task
            if lesson.objectives:
                objectives = lesson.objectives

    context = {
        "student_name": child.name,
        "level": level_num,
        "level_label": level_label,
        "subject": subject,
        "lesson_topic": lesson_title,
        "day_number": day_number,
        "activity_type": "Explore" if day_number == 1 else "Practice" if day_number == 2 else "Apply",
        "learning_objectives": objectives,
        "task_instructions": task_instructions
    }

    eval_result = await evaluate_student_work(
        student_name=child.name,
        context=context,
        submission_text=content or "Uploaded file evidence",
        file_name=file_name
    )

    evidence = LearningEvidence(
        child_id=child_id,
        lesson_id=lesson_id,
        day_number=day_number,
        subject=subject,
        lesson_title=lesson_title,
        skill=skill,
        evidence_type=evidence_type,
        submission_type="file" if saved_file_url else submission_type,
        content=content,
        file_upload=saved_file_url,
        score=eval_result["score"],
        ai_feedback=eval_result["ai_feedback"],
        verified=eval_result["verified"]
    )
    db.add(evidence)

    # Mark day & lesson completed in progress
    if lesson_id:
        progress = db.query(StudentProgress).filter(
            StudentProgress.child_id == child_id,
            StudentProgress.lesson_id == lesson_id,
            StudentProgress.day_number == day_number
        ).first()
        if not progress:
            progress = StudentProgress(
                child_id=child_id,
                lesson_id=lesson_id,
                day_number=day_number,
                activity_type=context["activity_type"],
                status="completed",
                quiz_score=eval_result["score"],
                mastery_status=eval_result.get("mastery_status", "competent")
            )
            db.add(progress)
        else:
            progress.status = "completed"
            progress.quiz_score = eval_result["score"]
            progress.mastery_status = eval_result.get("mastery_status", "competent")

    # Reward XP
    child.xp += 25
    
    # Log AI evaluation interaction
    interaction = AIInteraction(
        child_id=child_id,
        lesson_id=lesson_id,
        day_number=day_number,
        role="assistant",
        prompt=content or file_name or "Evidence Submission",
        response=eval_result["ai_feedback"]
    )
    db.add(interaction)

    db.commit()
    db.refresh(evidence)

    return evidence

@router.get("/portfolio/{child_id}", response_model=List[EvidenceOut])
def get_portfolio(child_id: int, db: Session = Depends(get_db)):
    return db.query(LearningEvidence).filter(LearningEvidence.child_id == child_id).order_by(LearningEvidence.created_at.desc()).all()
