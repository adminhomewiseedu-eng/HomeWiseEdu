from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ..database import get_db
from ..models import Child, Subject, Unit, Lesson, LessonDay, StudentProgress, LearningEvidence, ChildSubject, User, LessonSession
from ..utils.levels import get_level_label
from .auth import get_current_user, authorize_child

router = APIRouter(prefix="/api/student", tags=["student"])

@router.get("/dashboard/{child_id}")
def get_student_dashboard(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    child = authorize_child(db, current_user, child_id)

    student_level = child.level if child.level is not None else 0
    edu_sys = child.education_system or "UK"
    level_label = get_level_label(student_level, edu_sys)

    # 1. Enrolled subjects for this student
    enrollments = db.query(ChildSubject).filter(ChildSubject.child_id == child.id).all()
    enrolled_subject_ids = [e.subject_id for e in enrollments]

    if not enrolled_subject_ids:
        # Default auto-enroll in Mathematics, English Language, Science
        default_subjs = db.query(Subject).filter(Subject.slug.in_(["mathematics", "english-language", "science"])).all()
        for s in default_subjs:
            db.add(ChildSubject(child_id=child.id, subject_id=s.id))
        db.commit()
        enrolled_subject_ids = [s.id for s in default_subjs]

    enrolled_subjects = db.query(Subject).filter(Subject.id.in_(enrolled_subject_ids)).all()

    # 2. Completed day records for this child
    completed_records = db.query(StudentProgress).filter(
        StudentProgress.child_id == child.id,
        StudentProgress.status == "completed"
    ).all()
    
    completed_pairs = {(r.lesson_id, r.day_number) for r in completed_records}
    completed_lessons_count = len({r.lesson_id for r in completed_records})

    # 3. Dynamic "Today's Lesson": Multi-Day Sequence Resolver
    available_lessons = (
        db.query(Lesson)
        .join(Unit, Lesson.unit_id == Unit.id)
        .filter(
            Lesson.level == student_level,
            Unit.subject_id.in_(enrolled_subject_ids)
        )
        .order_by(Unit.order_num.asc(), Lesson.order_num.asc())
        .all()
    )
    available_lessons = [lesson for lesson in available_lessons if any(
        (day.status or "").lower() in {"active", "published"} for day in lesson.days
    ) or not lesson.days]

    current_lesson = None
    current_day_number = 1
    current_activity_type = "Explore"
    current_lesson_day = None

    for l in available_lessons:
        # Check Days 1, 2, 3 in order
        days = db.query(LessonDay).filter(
            LessonDay.lesson_id == l.id,
            LessonDay.status.in_(["active", "published"])
        ).order_by(LessonDay.day_number.asc()).all()
        if not days:
            # Fallback if days not yet seeded for this lesson
            if (l.id, 1) not in completed_pairs:
                current_lesson = l
                current_day_number = 1
                current_activity_type = "Explore"
                break
        else:
            incomplete_day = next((d for d in days if (l.id, d.day_number) not in completed_pairs), None)
            if incomplete_day:
                current_lesson = l
                current_day_number = incomplete_day.day_number
                current_activity_type = incomplete_day.activity_type
                current_lesson_day = incomplete_day
                break

    # If all lessons/days are completed, loop to first available
    if not current_lesson:
        if available_lessons:
            current_lesson = available_lessons[0]
            current_day_number = 1
            current_activity_type = "Explore"

    today_lesson_payload = None
    if current_lesson:
        unit_title = current_lesson.unit.title if current_lesson.unit else "General Unit"
        subj_title = current_lesson.unit.subject.title if current_lesson.unit and current_lesson.unit.subject else "General"
        subj_icon = current_lesson.unit.subject.icon if current_lesson.unit and current_lesson.unit.subject else "📐"
        
        today_lesson_payload = {
            "id": current_lesson.id,
            "lesson_id": current_lesson.id,
            "title": current_lesson.title,
            "subject": subj_title,
            "unit": unit_title,
            "level": current_lesson.level,
            "level_label": level_label,
            "day_number": current_day_number,
            "activity_type": current_activity_type,
            "order_num": current_lesson.order_num,
            "lesson_number": current_lesson.order_num,
            "icon": subj_icon,
            "xp_reward": 35,
            "estimated_duration": current_lesson_day.estimated_duration if current_lesson_day else "20 mins",
            "bible_reference": current_lesson_day.bible_reference if current_lesson_day else current_lesson.bible_reflection,
            "character_reference": current_lesson_day.character_reference if current_lesson_day else current_lesson.character_connection,
            "completed": (current_lesson.id, current_day_number) in completed_pairs
        }
        active_session = db.query(LessonSession).filter(
            LessonSession.child_id == child.id,
            LessonSession.lesson_id == current_lesson.id,
            LessonSession.day_number == current_day_number
        ).first()
        active_state = active_session.pedagogical_state if active_session else {}
        today_lesson_payload["practice_ready"] = bool(
            active_state.get("practice_ready") or active_state.get("current_phase") == "PRACTICE_READY"
        )

    # 4. Subject Progress Breakdown based strictly on child's enrolled subjects
    progress_by_subject = []
    for subj in enrolled_subjects:
        subj_lessons = (
            db.query(Lesson)
            .join(Unit, Lesson.unit_id == Unit.id)
            .filter(Unit.subject_id == subj.id, Lesson.level == student_level)
            .all()
        )
        subj_lessons = [lesson for lesson in subj_lessons if any(
            (day.status or "").lower() in {"active", "published"} for day in lesson.days
        ) or not lesson.days]
        total_subj_lessons = len(subj_lessons)
        if total_subj_lessons > 0:
            subj_lesson_ids = {l.id for l in subj_lessons}
            completed_in_subj = len({r.lesson_id for r in completed_records if r.lesson_id in subj_lesson_ids})
            pct = int((completed_in_subj / total_subj_lessons) * 100)
        else:
            pct = 0

        progress_by_subject.append({
            "subject": subj.title,
            "percentage": pct,
            "color": subj.color,
            "icon": subj.icon
        })

    # 5. Query real Projects and Learning Evidence
    evidence_items = (
        db.query(LearningEvidence)
        .filter(LearningEvidence.child_id == child_id)
        .order_by(LearningEvidence.created_at.desc())
        .limit(10)
        .all()
    )

    recent_projects = []
    learning_evidence_list = []
    for ev in evidence_items:
        item = {
            "id": ev.id,
            "title": f"{ev.subject} · {ev.lesson_title}",
            "subject": ev.subject,
            "skill": ev.skill,
            "evidence_type": ev.evidence_type,
            "submission_type": ev.submission_type,
            "verified": ev.verified,
            "status": "Done" if ev.verified else "In Review",
            "score": ev.score,
            "feedback": ev.ai_feedback
        }
        if ev.evidence_type == "project":
            recent_projects.append(item)
        learning_evidence_list.append(item)

    # 6. Dynamic AI Feedback snippet
    if evidence_items:
        latest_ev = evidence_items[0]
        feedback_text = latest_ev.ai_feedback
    else:
        feedback_text = f"Welcome, {child.name}! Start your {level_label} lesson today to earn XP and build your learning portfolio! 🌟"

    return {
        "id": child.id,
        "name": child.name,
        "level": student_level,
        "level_label": level_label,
        "education_system": edu_sys,
        "xp": child.xp,
        "streak_days": child.streak_days,
        "badges_count": min(completed_lessons_count, 12),
        "completed_lessons_count": completed_lessons_count,
        "today_lesson": today_lesson_payload,
        "progress_by_subject": progress_by_subject,
        "recent_projects": recent_projects,
        "learning_evidence": learning_evidence_list,
        "ai_feedback_snippet": feedback_text
    }
