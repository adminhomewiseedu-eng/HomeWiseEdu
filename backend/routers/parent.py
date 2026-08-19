from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..models import User, Child, ParentAlert, AIRecommendation, LearningEvidence, StudentProgress, Lesson, Unit, ChildSubject
from ..schemas import RecommendationAction
from ..utils.levels import get_level_label
from .auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/parent", tags=["parent"])

@router.get("/dashboard/{parent_id}")
def get_parent_dashboard(
    parent_id: int, 
    db: Session = Depends(get_db),
    auth_user_id: Optional[int] = Depends(get_current_user_id)
):
    target_id = auth_user_id or parent_id
    parent = db.query(User).filter(User.id == target_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    children = db.query(Child).filter(Child.parent_id == target_id).all()
    children_data = []

    for c in children:
        edu_sys = c.education_system or "UK"
        lvl = c.level if c.level is not None else 0
        level_label = get_level_label(lvl, edu_sys)

        # Enrolled subjects
        enrollments = db.query(ChildSubject).filter(ChildSubject.child_id == c.id).all()
        enrolled_ids = [e.subject_id for e in enrollments]

        # Total lessons in enrolled subjects at child's level
        total_enrolled_lessons = (
            db.query(Lesson)
            .join(Unit, Lesson.unit_id == Unit.id)
            .filter(Lesson.level == lvl, Unit.subject_id.in_(enrolled_ids))
            .count()
        )
        if total_enrolled_lessons == 0:
            total_enrolled_lessons = max(1, db.query(Lesson).filter(Lesson.level == lvl).count())

        completed = db.query(StudentProgress).filter(
            StudentProgress.child_id == c.id, StudentProgress.status == "completed"
        ).count()

        progress_pct = min(100, int((completed / total_enrolled_lessons) * 100)) if total_enrolled_lessons > 0 else 0
        has_high_alert = db.query(ParentAlert).filter(
            ParentAlert.child_id == c.id, ParentAlert.severity == "high"
        ).count() > 0

        children_data.append({
            "id": c.id,
            "name": c.name,
            "age": c.age,
            "education_system": edu_sys,
            "level": lvl,
            "level_label": level_label,
            "grade": level_label,
            "avatar": c.avatar,
            "xp": c.xp,
            "streak_days": c.streak_days,
            "completed_lessons": completed,
            "certificates_count": max(0, completed // 3),
            "progress_percentage": progress_pct,
            "status_badge": "Needs attention" if has_high_alert else ("Just started" if completed == 0 else "Doing great!")
        })

    alerts = db.query(ParentAlert).filter(ParentAlert.parent_id == parent_id).order_by(ParentAlert.created_at.desc()).all()
    recommendations = db.query(AIRecommendation).filter(AIRecommendation.parent_id == parent_id).order_by(AIRecommendation.created_at.desc()).all()
    
    child_ids = [c.id for c in children]
    recent_evidence = db.query(LearningEvidence).filter(
        LearningEvidence.child_id.in_(child_ids)
    ).order_by(LearningEvidence.created_at.desc()).limit(6).all() if child_ids else []

    return {
        "parent_name": parent.name.split()[0] if parent.name else "Parent",
        "children": children_data,
        "weekly_summary": {
            "strengths": "No activity yet — complete daily lessons to view strengths" if not recent_evidence else f"Completed {sum(c['completed_lessons'] for c in children_data)} lesson activities across all enrolled subjects with strong engagement.",
            "needs_improvement": "Maintain a regular daily lesson cadence to reinforce newly learned concepts.",
            "bible_reflection": "Proverbs 22:6 — 'Train up a child in the way he should go, and when he is old he will not depart from it.'"
        },
        "alerts": alerts,
        "recommendations": recommendations,
        "recent_evidence": recent_evidence
    }

@router.post("/recommendations/{rec_id}/action")
def handle_recommendation_action(rec_id: int, action: RecommendationAction, db: Session = Depends(get_db)):
    rec = db.query(AIRecommendation).filter(AIRecommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.status = "approved" if action.action == "approve" else "overridden"
    db.commit()
    return {"message": f"Recommendation {rec.status}", "status": rec.status}
