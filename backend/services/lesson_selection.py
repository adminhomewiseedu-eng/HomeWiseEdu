"""Homeschool planning and browsing. Never writes learning progress."""
from fastapi import HTTPException
from ..models import Lesson, LessonDay, Unit, ChildSubject, StudentProgress, LessonSession, LessonAssignment
from ..routers.auth import authorize_child, authorize_child_lesson, effective_child_programme


def homeschool_child(db, user, child_id, *, planning=False):
    child = authorize_child(db, user, child_id)
    if planning and user.role not in {"parent", "admin"}:
        raise HTTPException(403, "Only parents can manage assignments")
    if effective_child_programme(child) != "homeschool":
        raise HTTPException(403, "Lesson planning is available for Homeschool children only")
    return child


def eligible_session(db, user, child_id, lesson_id, day_number):
    child = homeschool_child(db, user, child_id)
    _, lesson = authorize_child_lesson(db, user, child.id, lesson_id)
    day = db.query(LessonDay).filter_by(lesson_id=lesson.id, day_number=day_number).first()
    if lesson.level != child.level or lesson.archived or not day or (day.status or "").lower() not in {"active", "published"}:
        raise HTTPException(404, "Published lesson session not available at this child's level")
    return lesson, day


def lesson_options(db, user, child_id):
    child = homeschool_child(db, user, child_id)
    subjects = db.query(ChildSubject.subject_id).filter_by(child_id=child.id)
    lessons = db.query(Lesson).join(Unit).filter(
        Unit.subject_id.in_(subjects), Lesson.level == child.level, Lesson.archived.is_(False)
    ).order_by(Unit.subject_id, Unit.order_num, Lesson.order_num, Lesson.id).all()
    progress = {(p.lesson_id, p.day_number): p for p in db.query(StudentProgress).filter_by(child_id=child.id)}
    sessions = {(s.lesson_id, s.day_number): s for s in db.query(LessonSession).filter_by(child_id=child.id)}
    result = []
    for lesson in lessons:
        for day in lesson.days:
            if (day.status or "").lower() not in {"active", "published"}:
                continue
            key = (lesson.id, day.day_number)
            session = sessions.get(key)
            state = (session.pedagogical_state or {}) if session else {}
            result.append({
                "id": lesson.id, "lesson_id": lesson.id, "day_number": day.day_number,
                "title": lesson.title, "session_title": day.title, "activity_type": day.activity_type,
                "subject_id": lesson.unit.subject_id, "subject": lesson.unit.subject.title,
                "icon": lesson.unit.subject.icon, "unit_id": lesson.unit_id, "unit": lesson.unit.title, "level": lesson.level,
                "curriculum_week": lesson.curriculum_week, "lesson_number": lesson.order_num,
                "status": progress[key].status if key in progress else ("in_progress" if session else "not_started"),
                "practice_ready": bool(state.get("practice_ready") or state.get("current_phase") == "PRACTICE_READY"),
            })
    return result


def assignment_payloads(db, user, child_id, *, include_unavailable=False):
    options = {(x["lesson_id"], x["day_number"]): x for x in lesson_options(db, user, child_id)}
    assignments = db.query(LessonAssignment).filter_by(child_id=child_id, cancelled=False).order_by(
        LessonAssignment.scheduled_date, LessonAssignment.priority, LessonAssignment.id
    ).all()
    result = []
    for a in assignments:
        session = options.get((a.lesson_id, a.day_number))
        if not session and not include_unavailable:
            continue
        result.append({**(session or {"lesson_id": a.lesson_id, "day_number": a.day_number,
            "title": "Assignment no longer available", "subject": "Unavailable session", "status": "unavailable"}),
            "available": session is not None, "assignment_id": a.id,
            "scheduled_date": a.scheduled_date, "priority": a.priority})
    return result
