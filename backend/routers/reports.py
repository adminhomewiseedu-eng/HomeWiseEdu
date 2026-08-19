from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ..database import get_db
from ..models import Child, User, StudentProgress, LearningEvidence, ChildSubject, Subject, Lesson
from ..utils.levels import get_level_label
from ..services.openai_service import generate_weekly_summary

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/student/{child_id}")
async def get_student_report(child_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Student not found")

    parent = db.query(User).filter(User.id == child.parent_id).first()
    edu_sys = child.education_system or "UK"
    level_num = child.level if child.level is not None else 4
    level_label = get_level_label(level_num, edu_sys)

    enrollments = db.query(ChildSubject).filter(ChildSubject.child_id == child_id).all()
    subject_ids = [e.subject_id for e in enrollments]
    enrolled_subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []

    completed_progress = db.query(StudentProgress).filter(
        StudentProgress.child_id == child_id,
        StudentProgress.status == "completed"
    ).all()

    evidence_records = db.query(LearningEvidence).filter(
        LearningEvidence.child_id == child_id
    ).order_by(LearningEvidence.created_at.desc()).all()

    # Subject breakdown
    subject_progress = []
    for s in enrolled_subjects:
        subj_lessons = db.query(Lesson).join(Lesson.unit).filter(Lesson.level == level_num, Lesson.unit.has(subject_id=s.id)).all()
        total_l = max(1, len(subj_lessons))
        comp_l = len([p for p in completed_progress if p.lesson_id in [l.id for l in subj_lessons]])
        subject_progress.append({
            "subject": s.title,
            "icon": s.icon,
            "completed": comp_l,
            "total": total_l,
            "percentage": min(100, int((comp_l / total_l) * 100))
        })

    # AI Summary
    summary_data = await generate_weekly_summary(
        student_name=child.name,
        activity_facts={
            "level": level_num,
            "level_label": level_label,
            "completed_count": len(completed_progress),
            "learning_highlights": f"Active across {len(enrolled_subjects)} subjects",
            "skills_demonstrated": ", ".join([e.skill for e in evidence_records[:4]]) or "Foundational core concepts",
            "scripture_character_notes": "Diligent, attentive, and engaged",
            "highlight_subject": enrolled_subjects[0].title if enrolled_subjects else "General"
        }
    )

    return {
        "student": {
            "id": child.id,
            "name": child.name,
            "age": child.age,
            "education_system": edu_sys,
            "level": level_num,
            "level_label": level_label,
            "avatar": child.avatar,
            "xp": child.xp,
            "streak_days": child.streak_days,
            "parent_name": parent.name if parent else "Parent"
        },
        "academic_pathway": [s.title for s in enrolled_subjects],
        "subject_progress": subject_progress,
        "completed_activities_count": len(completed_progress),
        "learning_evidence": [
            {
                "id": ev.id,
                "subject": ev.subject,
                "lesson_title": ev.lesson_title,
                "skill": ev.skill,
                "score": ev.score,
                "ai_feedback": ev.ai_feedback,
                "verified": ev.verified,
                "created_at": ev.created_at.strftime("%Y-%m-%d") if ev.created_at else ""
            }
            for ev in evidence_records
        ],
        "summary": summary_data
    }
