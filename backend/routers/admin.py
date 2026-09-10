import datetime
import hashlib
import secrets
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..models import (AIInteraction, AdminProfile, Child, ChildSubject, LearningEvidence, Lesson, LessonDay,
                      LessonSession, ParentProfile, PasswordResetToken, StudentProgress, Subject, Unit, User)
from ..schemas import AdminChangePassword, AdminParentCreate, AdminParentStatusUpdate, AdminParentUpdate, AdminProfileUpdate
from ..services.password_reset_email import email_delivery_configured, send_password_reset_email
from ..services.storage_service import delete_profile_image, save_profile_image
from ..utils.levels import get_level_label
from .auth import get_password_hash, require_admin, verify_password

router = APIRouter(prefix="/api/admin", tags=["admin"])
PUBLISHED = {"active", "published"}


def _admin_profile_payload(admin: User, profile: AdminProfile | None) -> dict:
    parts = (admin.name or "").strip().split(maxsplit=1)
    first = profile.first_name if profile and profile.first_name is not None else (parts[0] if parts else "")
    last = profile.last_name if profile and profile.last_name is not None else (parts[1] if len(parts) > 1 else "")
    return {
        "id": admin.id, "first_name": first, "last_name": last, "name": admin.name,
        "email": admin.email, "phone_number": profile.phone_number if profile else None,
        "address_line_1": profile.address_line_1 if profile else None,
        "address_line_2": profile.address_line_2 if profile else None,
        "city": profile.city if profile else None, "state_region": profile.state_region if profile else None,
        "postal_code": profile.postal_code if profile else None, "country": profile.country if profile else None,
        "profile_image_url": "/api/admin/profile/image" if profile and profile.profile_image_name else None,
        "role": "Administrator", "account_status": (admin.account_status or "active").title(),
        "joined_at": admin.created_at, "updated_at": admin.updated_at,
    }


def _published_lesson(lesson: Lesson) -> bool:
    return bool(lesson.days) and all((day.status or "").lower() in PUBLISHED for day in lesson.days)


def _evidence_state(item: LearningEvidence) -> str:
    if item.verified:
        return "verified"
    if item.score is None:
        return "pending"
    return "needs_review"


def _parent_or_404(db: Session, parent_id: int) -> User:
    parent = db.query(User).filter(User.id == parent_id, User.role == "parent").first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


def _profile_value(profile: ParentProfile | None, field: str):
    return getattr(profile, field, None) if profile else None


def _send_setup_link(db: Session, parent: User) -> bool:
    if not email_delivery_configured():
        return False
    now = datetime.datetime.utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == parent.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=parent.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=now + datetime.timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    ))
    db.commit()
    reset_url = f"{settings.FRONTEND_URL}/reset-password?{urlencode({'token': raw_token})}"
    return send_password_reset_email(parent.email, reset_url)


def _parent_detail_payload(db: Session, parent: User) -> dict:
    profile = parent.parent_profile
    children = []
    for child in parent.children:
        subjects = [item.subject.title for item in child.enrolled_subjects if item.subject]
        progress = child.progress_records
        completed = sum(item.status == "completed" for item in progress)
        children.append({
            "id": child.id, "name": child.name, "avatar": child.avatar,
            "profile_image_url": f"/api/parent/children/{child.id}/profile-image" if child.profile_image_name else None,
            "level": child.level, "level_label": get_level_label(child.level, child.education_system),
            "education_system": child.education_system, "subjects": subjects,
            "progress_percentage": round(completed / len(progress) * 100) if progress else 0,
            "account_status": "active" if child.active else "inactive",
            "login_enabled": bool(child.login_user),
        })
    name_parts = (parent.name or "").split(maxsplit=1)
    return {
        "id": parent.id,
        "name": parent.name,
        "first_name": _profile_value(profile, "first_name") or (name_parts[0] if name_parts else ""),
        "last_name": _profile_value(profile, "last_name") or (name_parts[1] if len(name_parts) > 1 else ""),
        "email": parent.email,
        "phone_number": _profile_value(profile, "phone_number"),
        "address_line_1": _profile_value(profile, "address_line_1"),
        "address_line_2": _profile_value(profile, "address_line_2"),
        "city": _profile_value(profile, "city"),
        "state_region": _profile_value(profile, "state_region"),
        "postal_code": _profile_value(profile, "postal_code"),
        "country": _profile_value(profile, "country"),
        "profile_image_url": f"/api/admin/parents/{parent.id}/profile-image" if profile and profile.profile_image_name else None,
        "role": parent.role,
        "account_status": parent.account_status or "active",
        "created_at": parent.created_at,
        "updated_at": parent.updated_at,
        "children": children,
        "total_children": len(children),
        "subscription": {"configured": False, "status": "not_configured", "message": "Subscription billing is not yet connected."},
    }


@router.get("/parents")
def list_parents(
    search: str = "", status: str = "", sort: str = "newest",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(require_admin),
):
    child_counts = db.query(Child.parent_id.label("parent_id"), func.count(Child.id).label("child_count")).group_by(Child.parent_id).subquery()
    query = db.query(User, ParentProfile, func.coalesce(child_counts.c.child_count, 0)).outerjoin(
        ParentProfile, ParentProfile.user_id == User.id
    ).outerjoin(child_counts, child_counts.c.parent_id == User.id).filter(User.role == "parent")
    if search.strip():
        needle = f"%{search.strip().lower()}%"
        query = query.filter(or_(func.lower(User.name).like(needle), func.lower(User.email).like(needle), func.lower(ParentProfile.phone_number).like(needle)))
    if status:
        query = query.filter(User.account_status == status.lower())
    total = query.count()
    orders = {
        "oldest": User.created_at.asc(), "name": func.lower(User.name).asc(),
        "children": func.coalesce(child_counts.c.child_count, 0).desc(), "newest": User.created_at.desc(),
    }
    rows = query.order_by(orders.get(sort, orders["newest"])).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [{
            "id": user.id, "name": user.name, "email": user.email,
            "phone_number": profile.phone_number if profile else None,
            "profile_image_url": f"/api/admin/parents/{user.id}/profile-image" if profile and profile.profile_image_name else None,
            "child_count": int(child_count), "account_status": user.account_status or "active",
            "subscription_status": "not_configured", "created_at": user.created_at,
        } for user, profile, child_count in rows],
        "page": page, "page_size": page_size, "total": total,
        "summary": {
            "total_parents": db.query(User).filter(User.role == "parent").count(),
            "active_parents": db.query(User).filter(User.role == "parent", User.account_status == "active").count(),
            "total_children": db.query(Child).count(),
            "subscriptions_configured": False,
        },
    }


@router.get("/parents/{parent_id}")
def parent_detail(parent_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    parent = db.query(User).options(
        selectinload(User.parent_profile),
        selectinload(User.children).selectinload(Child.enrolled_subjects).selectinload(ChildSubject.subject),
        selectinload(User.children).selectinload(Child.progress_records),
        selectinload(User.children).selectinload(Child.login_user),
    ).filter(User.id == parent_id, User.role == "parent").first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return _parent_detail_payload(db, parent)


@router.post("/parents", status_code=201)
def create_parent(payload: AdminParentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    if db.query(User).filter(func.lower(User.email) == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    first, last = payload.first_name.strip(), payload.last_name.strip()
    if not first or not last:
        raise HTTPException(status_code=422, detail="First name and last name are required")
    parent = User(
        email=payload.email, name=f"{first} {last}", role="parent", account_status="active",
        avatar=first[0].upper(), password_hash=get_password_hash(secrets.token_urlsafe(32)),
    )
    db.add(parent); db.flush()
    profile_values = payload.model_dump(exclude={"email"})
    db.add(ParentProfile(user_id=parent.id, **{key: (value.strip() if isinstance(value, str) else value) for key, value in profile_values.items()}))
    db.commit(); db.refresh(parent)
    invitation_sent = _send_setup_link(db, parent)
    return {"parent": _parent_detail_payload(db, parent), "invitation_sent": invitation_sent,
            "message": "Parent created and setup email sent." if invitation_sent else "Parent created, but email delivery is unavailable. Use Reset password when delivery is configured."}


@router.patch("/parents/{parent_id}")
def update_parent(parent_id: int, changes: AdminParentUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    parent = _parent_or_404(db, parent_id)
    profile = parent.parent_profile or ParentProfile(user_id=parent.id)
    if not parent.parent_profile:
        db.add(profile)
    values = changes.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(profile, field, value.strip() if isinstance(value, str) else value)
    first = profile.first_name or (parent.name.split(maxsplit=1)[0] if parent.name else "")
    last = profile.last_name or (parent.name.split(maxsplit=1)[1] if len(parent.name.split(maxsplit=1)) > 1 else "")
    parent.name = " ".join(part for part in (first, last) if part).strip()
    parent.avatar = (first or last or "P")[0].upper()
    parent.updated_at = datetime.datetime.utcnow()
    db.commit(); db.refresh(parent)
    return _parent_detail_payload(db, parent)


@router.patch("/parents/{parent_id}/status")
def update_parent_status(parent_id: int, change: AdminParentStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    parent = _parent_or_404(db, parent_id)
    parent.account_status = change.status
    parent.auth_version = (parent.auth_version or 0) + 1
    parent.updated_at = datetime.datetime.utcnow()
    db.commit(); db.refresh(parent)
    return {"id": parent.id, "account_status": parent.account_status}


@router.post("/parents/{parent_id}/reset-password")
def send_parent_reset(parent_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    parent = _parent_or_404(db, parent_id)
    if not email_delivery_configured():
        raise HTTPException(status_code=503, detail="Password reset email delivery is not configured")
    sent = _send_setup_link(db, parent)
    if not sent:
        raise HTTPException(status_code=502, detail="Password reset email could not be sent")
    return {"message": "Password reset email sent."}


@router.get("/parents/{parent_id}/profile-image")
def parent_profile_image(parent_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    parent = _parent_or_404(db, parent_id)
    profile = parent.parent_profile
    if not profile or not profile.profile_image_name:
        raise HTTPException(status_code=404, detail="Profile picture is not available")
    root = Path(settings.PROFILE_IMAGE_DIR).resolve()
    target = (root / profile.profile_image_name).resolve()
    if target.parent != root or not target.is_file():
        raise HTTPException(status_code=404, detail="Profile picture is not available")
    return FileResponse(target)


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
            "id": child.id, "name": child.name, "avatar": child.avatar,
            "profile_image_url": f"/api/parent/children/{child.id}/profile-image" if child.profile_image_name else None,
            "student_email": child.login_user.email if child.login_user else None,
            "parent": child.parent.name if child.parent else None,
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
        "student": {"id": child.id, "name": child.name, "avatar": child.avatar,
                    "profile_image_url": f"/api/parent/children/{child.id}/profile-image" if child.profile_image_name else None,
                    "student_email": child.login_user.email if child.login_user else None,
                    "age": child.age, "active": child.active,
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
    return {"platform": {"name": "HomeWiseEdu", "domain": "homewiseedu.com", "support_email": "support@homewiseedu.com", "environment": settings.ENVIRONMENT},
            "academic": {"education_systems": ["UK", "USA", "Canada", "Australia"], "levels": list(range(14)),
                         "subjects": [subject.title for subject in db.query(Subject).order_by(Subject.title.asc()).all()]},
            "ai": {"openai": "configured" if settings.OPENAI_API_KEY else "not_configured",
                   "openai_model": settings.OPENAI_MODEL if settings.OPENAI_API_KEY else None,
                   "realtime": "configured" if settings.OPENAI_API_KEY else "not_configured",
                   "realtime_model": settings.OPENAI_REALTIME_MODEL if settings.OPENAI_API_KEY else None,
                   "active_voice_provider": "OpenAI Realtime/WebRTC",
                   "elevenlabs_active_classroom": False},
            "subscriptions": {"stripe": "not_connected"}}


@router.get("/profile")
def get_admin_profile(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return _admin_profile_payload(current_user, current_user.admin_profile)


@router.patch("/profile")
def update_admin_profile(changes: AdminProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    profile = current_user.admin_profile or AdminProfile(user_id=current_user.id)
    if not current_user.admin_profile:
        db.add(profile)
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(profile, field, value.strip() if isinstance(value, str) else value)
    parts = (current_user.name or "").split(maxsplit=1)
    first = profile.first_name or (parts[0] if parts else "")
    last = profile.last_name or (parts[1] if len(parts) > 1 else "")
    current_user.name = " ".join(part for part in (first, last) if part).strip()
    current_user.avatar = (first or last or "A")[0].upper()
    current_user.updated_at = datetime.datetime.utcnow()
    db.commit(); db.refresh(current_user)
    return _admin_profile_payload(current_user, profile)


@router.post("/profile/image")
async def upload_admin_profile_image(image: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    profile = current_user.admin_profile or AdminProfile(user_id=current_user.id)
    if not current_user.admin_profile:
        db.add(profile)
    old_name = profile.profile_image_name
    profile.profile_image_name = await save_profile_image(image)
    current_user.updated_at = datetime.datetime.utcnow()
    db.commit()
    delete_profile_image(old_name)
    return {"profile_image_url": "/api/admin/profile/image"}


@router.get("/profile/image")
def admin_profile_image(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    profile = current_user.admin_profile
    if not profile or not profile.profile_image_name:
        raise HTTPException(status_code=404, detail="Profile picture is not available")
    root = Path(settings.PROFILE_IMAGE_DIR).resolve()
    target = (root / profile.profile_image_name).resolve()
    if target.parent != root or not target.is_file():
        raise HTTPException(status_code=404, detail="Profile picture is not available")
    return FileResponse(target)


@router.post("/change-password")
def change_admin_password(payload: AdminChangePassword, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="New password must be different from the current password")
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.auth_version = (current_user.auth_version or 0) + 1
    current_user.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Password changed successfully. Please log in again."}


@router.get("/content")
def content_status(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return {"supported_content_types": ["reading_recommendations", "bible_character_resources"],
            "reading_recommendations": sum(len(day.reading_recommendations or []) for day in db.query(LessonDay).all()),
            "message": "Announcements, templates, and platform messages do not have persistence yet."}
