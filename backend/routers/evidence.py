from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import LearningEvidence, Child, Lesson, LessonDay, StudentProgress, AIInteraction, User
from ..schemas import EvidenceOut
from ..services.openai_service import evaluate_student_work
from ..services.storage_service import save_evidence_upload
from ..config import settings
from ..utils.levels import get_level_label
from .auth import get_current_user, authorize_child

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    child = authorize_child(db, current_user, child_id)

    saved_file_url = None
    file_name = None
    if file and file.filename:
        saved_file_url, file_name = await save_evidence_upload(file)

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
        stored_file_name=file_name,
        score=eval_result["score"],
        ai_feedback=eval_result["ai_feedback"],
        verified=eval_result["verified"]
    )
    db.add(evidence)
    db.flush()
    if saved_file_url:
        evidence.file_upload = f"/api/evidence/{evidence.id}/file"

    evaluation_verified = (
        eval_result.get("verified") is True
        and eval_result.get("score") is not None
        and eval_result.get("mastery_status") not in {None, "pending_review"}
    )

    # Completion-dependent progress is granted only after verified evaluation.
    if lesson_id and evaluation_verified:
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

    # Pending review evidence is saved, but earns no completion XP or mastery.
    if evaluation_verified:
        child.xp += 25
        evidence.completion_xp_awarded = True
    
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


@router.get("/{evidence_id}/file")
def download_evidence_file(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evidence = db.query(LearningEvidence).filter(LearningEvidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    authorize_child(db, current_user, evidence.child_id)
    stored_name = getattr(evidence, "stored_file_name", None)
    if not stored_name:
        raise HTTPException(status_code=404, detail="Evidence file is not available")
    target = (Path(settings.EVIDENCE_DIR) / stored_name).resolve()
    if target.parent != Path(settings.EVIDENCE_DIR).resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Evidence file is not available")
    return FileResponse(target, filename=f"evidence{target.suffix}")


@router.post("/{evidence_id}/retry-evaluation", response_model=EvidenceOut)
async def retry_evidence_evaluation(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evidence = db.query(LearningEvidence).filter(LearningEvidence.id == evidence_id).with_for_update().first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    child = authorize_child(db, current_user, evidence.child_id)
    if evidence.verified and evidence.score is not None:
        return evidence

    lesson = db.query(Lesson).filter(Lesson.id == evidence.lesson_id).first() if evidence.lesson_id else None
    level_num = child.level if child.level is not None else 0
    level_label = get_level_label(level_num, child.education_system or "UK")
    objectives = lesson.objectives if lesson and lesson.objectives else [evidence.skill]
    task = lesson.default_evidence_task if lesson and lesson.default_evidence_task else "Demonstrate your understanding and show your step-by-step working."
    context = {
        "student_name": child.name, "level": level_num, "level_label": level_label,
        "subject": evidence.subject, "lesson_topic": evidence.lesson_title,
        "day_number": evidence.day_number,
        "activity_type": "Explore" if evidence.day_number == 1 else "Practice" if evidence.day_number == 2 else "Apply",
        "learning_objectives": objectives, "task_instructions": task,
    }
    result = await evaluate_student_work(
        student_name=child.name,
        context=context,
        submission_text=evidence.content or "Uploaded file evidence",
        file_name=evidence.stored_file_name,
    )
    verified = result.get("verified") is True and result.get("score") is not None and result.get("mastery_status") not in {None, "pending_review"}
    evidence.score = result.get("score")
    evidence.ai_feedback = result.get("ai_feedback", "Evaluation remains pending review.")
    evidence.verified = verified
    if verified:
        if evidence.lesson_id:
            progress = db.query(StudentProgress).filter(
                StudentProgress.child_id == child.id,
                StudentProgress.lesson_id == evidence.lesson_id,
                StudentProgress.day_number == evidence.day_number,
            ).first()
            if not progress:
                progress = StudentProgress(child_id=child.id, lesson_id=evidence.lesson_id,
                    day_number=evidence.day_number, activity_type=context["activity_type"], status="completed")
                db.add(progress)
            progress.status = "completed"
            progress.quiz_score = result["score"]
            progress.mastery_status = result["mastery_status"]
        if not evidence.completion_xp_awarded:
            child.xp += 25
            evidence.completion_xp_awarded = True
    db.add(AIInteraction(child_id=child.id, lesson_id=evidence.lesson_id, day_number=evidence.day_number,
                         role="assistant", prompt="Pending evidence retry", response=evidence.ai_feedback))
    db.commit()
    db.refresh(evidence)
    return evidence

@router.get("/portfolio/{child_id}", response_model=List[EvidenceOut])
def get_portfolio(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    authorize_child(db, current_user, child_id)
    return db.query(LearningEvidence).filter(LearningEvidence.child_id == child_id).order_by(LearningEvidence.created_at.desc()).all()
