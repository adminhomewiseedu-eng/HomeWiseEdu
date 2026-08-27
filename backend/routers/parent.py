from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..models import User, Child, ParentAlert, AIRecommendation, LearningEvidence, StudentProgress, Lesson, Unit, ChildSubject, Subject
from ..schemas import RecommendationAction, ChildUpdate, StudentCredentialsUpdate
from ..config import settings
from ..services.storage_service import save_profile_image, delete_profile_image
from ..utils.levels import get_level_label
from .auth import get_current_user, authorize_child, get_password_hash
from typing import Optional

router = APIRouter(prefix="/api/parent", tags=["parent"])


def _parent_owned_child(db: Session, current_user: User, child_id: int) -> Child:
    if current_user.role not in {"parent", "admin"}:
        raise HTTPException(status_code=403, detail="Parent access required")
    child = authorize_child(db, current_user, child_id)
    return child


def _child_payload(child: Child) -> dict:
    return {
        "id": child.id, "parent_id": child.parent_id, "name": child.name, "age": child.age,
        "date_of_birth": child.date_of_birth, "education_system": child.education_system,
        "level": child.level, "grade": get_level_label(child.level, child.education_system),
        "avatar": child.avatar, "xp": child.xp, "streak_days": child.streak_days,
        "student_email": child.login_user.email if child.login_user else None,
        "profile_image_url": f"/api/parent/children/{child.id}/profile-image" if child.profile_image_name else None,
    }

@router.get("/dashboard/{parent_id}")
def get_parent_dashboard(
    parent_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin" and current_user.id != parent_id:
        raise HTTPException(status_code=403, detail="Cannot access another parent's dashboard")
    if current_user.role not in {"parent", "admin"}:
        raise HTTPException(status_code=403, detail="Parent access required")
    target_id = parent_id
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
            "profile_image_url": f"/api/parent/children/{c.id}/profile-image" if c.profile_image_name else None,
            "student_email": c.login_user.email if c.login_user else None,
            "xp": c.xp,
            "streak_days": c.streak_days,
            "completed_lessons": completed,
            "certificates_count": max(0, completed // 3),
            "progress_percentage": progress_pct,
            "status_badge": "Needs attention" if has_high_alert else ("Just started" if completed == 0 else "Doing great!")
        })

    alerts = db.query(ParentAlert).filter(ParentAlert.parent_id == target_id).order_by(ParentAlert.created_at.desc()).all()
    recommendations = db.query(AIRecommendation).filter(AIRecommendation.parent_id == target_id).order_by(AIRecommendation.created_at.desc()).all()
    
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


@router.patch("/children/{child_id}")
def update_child(
    child_id: int,
    changes: ChildUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    child = _parent_owned_child(db, current_user, child_id)
    values = changes.model_dump(exclude_unset=True)
    subject_ids = values.pop("subject_ids", None)
    for field in ("name", "age", "date_of_birth", "education_system", "avatar"):
        if field in values and values[field] is not None:
            setattr(child, field, values[field])
    if "level" in values and values["level"] is not None:
        child.level = max(0, min(13, int(values["level"])))
    child.grade = get_level_label(child.level, child.education_system)
    if child.login_user:
        child.login_user.name = child.name
        child.login_user.avatar = child.avatar
    if subject_ids is not None:
        valid = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
        if len(valid) != len(set(subject_ids)):
            raise HTTPException(status_code=400, detail="One or more selected subjects are invalid")
        db.query(ChildSubject).filter(ChildSubject.child_id == child.id).delete(synchronize_session=False)
        for subject in valid:
            db.add(ChildSubject(child_id=child.id, subject_id=subject.id))
    db.commit()
    db.refresh(child)
    return _child_payload(child)


@router.put("/children/{child_id}/credentials")
def update_student_credentials(
    child_id: int,
    changes: StudentCredentialsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    child = _parent_owned_child(db, current_user, child_id)
    email = (changes.email or "").strip().lower()
    password = changes.password or ""
    if not child.login_user and (not email or not password):
        raise HTTPException(status_code=400, detail="Email and password are required to enable student login")
    if email and "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid student email")
    if password and len(password) < 8:
        raise HTTPException(status_code=400, detail="Student password must be at least 8 characters")
    account = child.login_user
    if email and db.query(User).filter(User.email == email, User.id != (account.id if account else -1)).first():
        raise HTTPException(status_code=400, detail="Student email is already registered")
    if not account:
        account = User(email=email, name=child.name, role="student", avatar=child.avatar,
                       password_hash=get_password_hash(password))
        db.add(account)
        db.flush()
        child.user_id = account.id
    else:
        if email and email != account.email:
            account.email = email
        if password:
            account.password_hash = get_password_hash(password)
    db.commit()
    return {"student_email": account.email, "login_enabled": True}


@router.post("/children/{child_id}/profile-image")
async def upload_child_profile_image(
    child_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    child = _parent_owned_child(db, current_user, child_id)
    old_name = child.profile_image_name
    new_name = await save_profile_image(image)
    child.profile_image_name = new_name
    db.commit()
    delete_profile_image(old_name)
    return {"profile_image_url": f"/api/parent/children/{child.id}/profile-image"}


@router.get("/children/{child_id}/profile-image")
def get_child_profile_image(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    child = authorize_child(db, current_user, child_id)
    if not child.profile_image_name:
        raise HTTPException(status_code=404, detail="Profile picture is not available")
    root = Path(settings.PROFILE_IMAGE_DIR).resolve()
    target = (root / child.profile_image_name).resolve()
    if target.parent != root or not target.is_file():
        raise HTTPException(status_code=404, detail="Profile picture is not available")
    return FileResponse(target)


@router.delete("/children/{child_id}/profile-image")
def remove_child_profile_image(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    child = _parent_owned_child(db, current_user, child_id)
    old_name = child.profile_image_name
    child.profile_image_name = None
    db.commit()
    delete_profile_image(old_name)
    return {"profile_image_url": None}

@router.post("/recommendations/{rec_id}/action")
def handle_recommendation_action(
    rec_id: int,
    action: RecommendationAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rec = db.query(AIRecommendation).filter(AIRecommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if current_user.role != "admin" and rec.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this recommendation")
    rec.status = "approved" if action.action == "approve" else "overridden"
    db.commit()
    return {"message": f"Recommendation {rec.status}", "status": rec.status}
