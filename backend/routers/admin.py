import datetime
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (AIInteraction, Child, ChildSubject, LearningEvidence, Lesson, LessonDay,
                      LessonSession, StudentProgress, Subject, Unit, User)
from ..utils.levels import get_level_label
from .auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])
PUBLISHED = {"active", "published"}


def _published_lesson(lesson: Lesson) -> bool:
    return bool(lesson.days) and all((day.status or "").lower() in PUBLISHED for day in lesson.days)


def _evidence_state(item: LearningEvidence) -> str:
    if item.verified:
        return "verified"
    if item.score is None:
        return "pending"
    return "needs_review"


@router.get("/dashboard")
def get_admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    lessons = db.query(Lesson).all()
    children = db.query(Child).all()
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    return {
        "admin_name": current_user.name,
        "stats": {
            "total_students": len(children),
            "active_students": sum(bool(child.active and child.last_active_date and child.last_active_date >= cutoff) for child in children),
            "parents": db.query(User).filter(User.role == "parent").count(),
            "total_lessons": len(lessons),
            "published_lessons": sum(_published_lesson(lesson) for lesson in lessons),
            "pending_curriculum_items": db.query(LessonDay).filter(func.lower(LessonDay.status) == "pending").count(),
            "total_evidence": db.query(LearningEvidence).count(),
            "certificates_issued": 0,
            "ai_tutor_sessions": db.query(LessonSession).count(),
            "active_subscriptions": None,
            "monthly_revenue": None,
        },
        "billing": {"connected": False, "message": "Subscription billing is not connected yet."},
    }


@router.get("/students")
def list_students(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    children = db.query(Child).order_by(Child.name.asc()).all()
    result = []
    for child in children:
        enrollments = db.query(ChildSubject).filter(ChildSubject.child_id == child.id).all()
        subjects = [item.subject.title for item in enrollments if item.subject]
        progress = db.query(StudentProgress).filter(StudentProgress.child_id == child.id).all()
        completed = [item for item in progress if item.status == "completed"]
        evidence_count = db.query(LearningEvidence).filter(LearningEvidence.child_id == child.id).count()
        session = db.query(LessonSession).filter(LessonSession.child_id == child.id).order_by(LessonSession.last_active_at.desc()).first()
        current = session.lesson.title if session and session.lesson else None
        result.append({
            "id": child.id, "name": child.name, "avatar": child.avatar, "parent": child.parent.name if child.parent else None,
            "level": child.level, "level_label": get_level_label(child.level, child.education_system),
            "education_system": child.education_system, "subjects": subjects,
            "overall_progress": round((len(completed) / len(progress)) * 100) if progress else 0,
            "current_lesson": current, "last_active": child.last_active_date, "evidence_count": evidence_count,
            "status": "active" if child.active else "inactive",
            "needs_support": any(item.remediation_needed for item in progress),
        })
    return result


@router.get("/students/{child_id}")
def student_detail(child_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Student not found")
    enrollments = db.query(ChildSubject).filter(ChildSubject.child_id == child.id).all()
    progress = db.query(StudentProgress).filter(StudentProgress.child_id == child.id).order_by(StudentProgress.completed_at.desc()).all()
    evidence = db.query(LearningEvidence).filter(LearningEvidence.child_id == child.id).order_by(LearningEvidence.created_at.desc()).all()
    sessions = db.query(LessonSession).filter(LessonSession.child_id == child.id).order_by(LessonSession.last_active_at.desc()).limit(20).all()
    return {
        "student": {"id": child.id, "name": child.name, "avatar": child.avatar, "age": child.age, "active": child.active,
                    "parent": child.parent.name if child.parent else None, "parent_email": child.parent.email if child.parent else None,
                    "level": child.level, "level_label": get_level_label(child.level, child.education_system),
                    "education_system": child.education_system, "subjects": [e.subject.title for e in enrollments if e.subject]},
        "progress": [{"lesson": item.lesson.title if item.lesson else None, "day": item.day_number, "status": item.status,
                      "score": item.quiz_score, "mastery": item.mastery_status, "remediation_needed": item.remediation_needed}
                     for item in progress],
        "evidence": [{"id": item.id, "subject": item.subject, "lesson": item.lesson_title, "skill": item.skill,
                      "score": item.score, "status": _evidence_state(item), "feedback": item.ai_feedback,
                      "created_at": item.created_at} for item in evidence],
        "sessions": [{"id": item.id, "lesson": item.lesson.title if item.lesson else None, "day": item.day_number,
                      "phase": (item.pedagogical_state or {}).get("current_phase", "Not started"),
                      "remediation_count": (item.pedagogical_state or {}).get("remediation_count", 0),
                      "practice_ready": bool((item.pedagogical_state or {}).get("practice_ready")),
                      "last_active": item.last_active_at} for item in sessions],
        "certificates": [],
    }


@router.get("/evidence")
def list_evidence(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    items = db.query(LearningEvidence).order_by(LearningEvidence.created_at.desc()).all()
    return [{"id": item.id, "student_id": item.child_id, "student": item.child.name if item.child else None,
             "subject": item.subject, "lesson": item.lesson_title, "skill": item.skill, "evidence_type": item.evidence_type,
             "submission_type": item.submission_type, "score": item.score, "status": _evidence_state(item),
             "feedback": item.ai_feedback, "content": item.content, "has_file": bool(item.stored_file_name),
             "created_at": item.created_at} for item in items]


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    progress = db.query(StudentProgress).all()
    interactions = db.query(AIInteraction).all()
    completed = [item for item in progress if item.status == "completed"]
    mastery = Counter(item.mastery_status or "unknown" for item in progress)
    subject_completed = Counter()
    for item in completed:
        if item.lesson and item.lesson.unit and item.lesson.unit.subject:
            subject_completed[item.lesson.unit.subject.title] += 1
    return {
        "engagement": {"lessons_started": len(progress), "lessons_completed": len(completed),
                       "average_progress": round(len(completed) / len(progress) * 100) if progress else 0,
                       "weekly_learning_activity": None},
        "academic": {"mastery_distribution": mastery, "completion_by_subject": subject_completed,
                     "remediation_frequency": sum(bool(item.remediation_needed) for item in progress)},
        "ai_usage": {"tutor_sessions": db.query(LessonSession).count(), "ai_interactions": len(interactions),
                     "evaluations": sum(item.prompt == "Pending evidence retry" for item in interactions),
                     "failed_requests": None, "voice_usage": None},
    }


@router.get("/reports")
def reports_index(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return [{"student_id": child.id, "student": child.name, "parent": child.parent.name if child.parent else None,
             "completed_lessons": db.query(StudentProgress).filter(StudentProgress.child_id == child.id,
                 StudentProgress.status == "completed").count(),
             "evidence_count": db.query(LearningEvidence).filter(LearningEvidence.child_id == child.id).count()}
            for child in db.query(Child).order_by(Child.name.asc()).all()]


@router.get("/ai-monitoring")
def ai_monitoring(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    sessions = db.query(LessonSession).all()
    phase_counts = Counter((item.pedagogical_state or {}).get("current_phase", "Not started") for item in sessions)
    return {"services": {"openai": bool(settings.OPENAI_API_KEY), "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
                         "voice_id_configured": bool(settings.ELEVENLABS_VOICE_ID)},
            "tutor_sessions": len(sessions), "ai_interactions": db.query(AIInteraction).count(),
            "pending_evaluations": db.query(LearningEvidence).filter(LearningEvidence.verified.is_(False)).count(),
            "total_remediations": sum((item.pedagogical_state or {}).get("remediation_count", 0) for item in sessions),
            "sessions_by_phase": phase_counts, "openai_failures": None, "tts_failures": None}


@router.get("/settings")
def admin_settings(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return {"platform": {"name": settings.PROJECT_NAME, "support_email": None, "environment": settings.ENVIRONMENT},
            "academic": {"education_systems": ["UK", "USA", "Canada", "Australia"], "levels": list(range(14)),
                         "subjects": [subject.title for subject in db.query(Subject).order_by(Subject.title.asc()).all()]},
            "ai": {"openai": "configured" if settings.OPENAI_API_KEY else "not_configured",
                   "openai_model": settings.OPENAI_MODEL if settings.OPENAI_API_KEY else None,
                   "elevenlabs": "configured" if settings.ELEVENLABS_API_KEY else "not_configured",
                   "voice_id": "configured" if settings.ELEVENLABS_VOICE_ID else "not_configured"},
            "subscriptions": {"stripe": "not_connected"}}


@router.get("/content")
def content_status(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return {"supported_content_types": ["reading_recommendations", "bible_character_resources"],
            "reading_recommendations": sum(len(day.reading_recommendations or []) for day in db.query(LessonDay).all()),
            "message": "Announcements, templates, and platform messages do not have persistence yet."}
