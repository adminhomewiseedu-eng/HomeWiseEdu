import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models import Child, LessonSession, QuizQuestion, StudentProgress, User
from backend.routers.auth import get_password_hash
from backend.routers.lessons import advance_pedagogical_state


client = TestClient(app)


def register_parent(label="parent"):
    suffix = uuid.uuid4().hex
    response = client.post("/api/auth/register", json={
        "name": f"{label} {suffix[:6]}",
        "email": f"{label}.{suffix}@example.com",
        "password": "SecurePassword123!",
        "role": "parent",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def add_child(parent_id, headers, label="Child"):
    response = client.post("/api/auth/add-child", headers=headers, json={
        "parent_id": parent_id,
        "name": f"{label} {uuid.uuid4().hex[:6]}",
        "age": 7,
        "education_system": "UK",
        "level": 0,
        "subject_ids": [],
        "avatar": "🦁",
    })
    assert response.status_code == 200, response.text
    return response.json()["id"]


def make_ready(child_id, lesson_id=1, day_number=1):
    state = advance_pedagogical_state(None, None, is_opening_turn=True)
    state = advance_pedagogical_state(state, "Ready")
    for _ in range(4):
        state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    correct = {"result": "correct", "can_advance": True}
    state = advance_pedagogical_state(state, "Correct answer", eval_result=correct)
    state = advance_pedagogical_state(state, "Correct guided step", eval_result=correct)
    state = advance_pedagogical_state(state, "Correct application", eval_result=correct)
    state = advance_pedagogical_state(state, "Correct mastery proof", eval_result=correct)
    state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    assert state["practice_ready"] is True

    db = SessionLocal()
    try:
        session = db.query(LessonSession).filter_by(
            child_id=child_id, lesson_id=lesson_id, day_number=day_number
        ).first()
        if not session:
            session = LessonSession(
                child_id=child_id,
                lesson_id=lesson_id,
                day_number=day_number,
                pedagogical_state=state,
                messages=[],
                is_completed=True,
            )
            db.add(session)
        else:
            session.pedagogical_state = state
            session.is_completed = True
        db.commit()
    finally:
        db.close()


def test_unauthenticated_student_endpoints_are_rejected():
    assert client.get("/api/student/dashboard/1").status_code == 401
    assert client.post("/api/voice/tts", json={"text": "hello"}).status_code == 401
    assert client.get("/api/reports/student/1").status_code == 401


def test_parent_cannot_access_another_parents_child():
    parent_a, headers_a = register_parent("parent-a")
    parent_b, headers_b = register_parent("parent-b")
    child_b = add_child(parent_b, headers_b, "B-child")
    assert client.get(f"/api/student/dashboard/{child_b}", headers=headers_a).status_code == 403
    assert client.get(f"/api/evidence/portfolio/{child_b}", headers=headers_a).status_code == 403
    assert client.get(f"/api/parent/dashboard/{parent_b}", headers=headers_a).status_code == 403


def test_non_admin_is_denied_and_public_signup_cannot_create_admin():
    _, headers = register_parent("ordinary")
    assert client.get("/api/admin/dashboard", headers=headers).status_code == 403
    response = client.post("/api/auth/register", json={
        "name": "Not Admin",
        "email": f"not-admin-{uuid.uuid4().hex}@example.com",
        "password": "SecurePassword123!",
        "role": "admin",
    })
    assert response.status_code == 403


def test_client_cannot_write_authoritative_session_state():
    parent_id, headers = register_parent("state-owner")
    child_id = add_child(parent_id, headers)
    payload = {
        "child_id": child_id,
        "lesson_id": 1,
        "day_number": 1,
        "current_tab": 0,
        "messages": [],
        "practice_ready": True,
        "pedagogical_state": {"practice_ready": True, "current_phase": "PRACTICE_READY"},
        "is_completed": True,
    }
    assert client.post("/api/lessons/session", headers=headers, json=payload).status_code == 422
    db = SessionLocal()
    try:
        assert db.query(LessonSession).filter_by(child_id=child_id, lesson_id=1, day_number=1).first() is None
    finally:
        db.close()


def test_quiz_start_and_submission_require_backend_readiness():
    parent_id, headers = register_parent("quiz-guard")
    child_id = add_child(parent_id, headers)
    assert client.get(
        "/api/lessons/1/quiz", headers=headers,
        params={"child_id": child_id, "day_number": 1}
    ).status_code == 409
    assert client.post("/api/lessons/submit-quiz", headers=headers, json={
        "child_id": child_id, "lesson_id": 1, "day_number": 1, "answers": []
    }).status_code == 409

    make_ready(child_id)
    start = client.get(
        "/api/lessons/1/quiz", headers=headers,
        params={"child_id": child_id, "day_number": 1}
    )
    assert start.status_code == 200
    questions = start.json()
    assert questions
    submission = client.post("/api/lessons/submit-quiz", headers=headers, json={
        "child_id": child_id,
        "lesson_id": 1,
        "day_number": 1,
        "answers": [{"question_id": q["id"], "selected_answer": q["correct_answer"]} for q in questions],
    })
    assert submission.status_code == 200


def test_day_scoped_sessions_and_duplicate_prevention():
    parent_id, headers = register_parent("day-scope")
    child_id = add_child(parent_id, headers)
    day_one = {
        "child_id": child_id, "lesson_id": 1, "day_number": 1,
        "current_tab": 2, "messages": [{"sender": "tutor", "text": "day one"}],
    }
    assert client.post("/api/lessons/session", headers=headers, json=day_one).status_code == 200
    assert client.post("/api/lessons/session", headers=headers, json=day_one).status_code == 200
    day_two = client.get(f"/api/lessons/session/{child_id}/1/2", headers=headers)
    assert day_two.status_code == 200
    assert day_two.json()["messages"] == []
    assert day_two.json()["pedagogical_state"] == {}

    db = SessionLocal()
    try:
        count = db.query(LessonSession).filter_by(child_id=child_id, lesson_id=1, day_number=1).count()
        assert count == 1
    finally:
        db.close()


def test_repeated_quiz_submission_awards_xp_only_once():
    parent_id, headers = register_parent("xp-idempotency")
    child_id = add_child(parent_id, headers)
    make_ready(child_id)
    questions = client.get(
        "/api/lessons/1/quiz", headers=headers,
        params={"child_id": child_id, "day_number": 1}
    ).json()
    payload = {
        "child_id": child_id, "lesson_id": 1, "day_number": 1,
        "answers": [{"question_id": q["id"], "selected_answer": q["correct_answer"]} for q in questions],
    }
    first = client.post("/api/lessons/submit-quiz", headers=headers, json=payload)
    second = client.post("/api/lessons/submit-quiz", headers=headers, json=payload)
    assert first.status_code == 200 and first.json()["xp_earned"] > 0
    assert second.status_code == 200 and second.json()["xp_earned"] == 0


def test_password_hashing_failure_fails_closed():
    with patch("backend.routers.auth.pwd_context.hash", side_effect=RuntimeError("hashing unavailable")):
        with pytest.raises(RuntimeError):
            get_password_hash("must-not-be-stored")
    assert not get_password_hash("normal-password").startswith("plain:")
