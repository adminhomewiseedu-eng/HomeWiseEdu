import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models import Child, LearningEvidence, LessonSession, StudentProgress
from backend.routers.lessons import advance_pedagogical_state


client = TestClient(app)


def parent_and_child():
    suffix = uuid.uuid4().hex
    registered = client.post("/api/auth/register", json={
        "name": "Phase Two Parent",
        "email": f"phase2.{suffix}@example.com",
        "password": "SecurePassword123!",
        "role": "parent",
    }).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    child = client.post("/api/auth/add-child", headers=headers, json={
        "parent_id": registered["user"]["id"],
        "name": "Phase Two Child",
        "age": 7,
        "education_system": "UK",
        "level": 0,
        "subject_ids": [],
        "avatar": "🦁",
    }).json()
    return child["id"], headers


def test_production_flow_populates_and_preserves_active_question_on_clarification():
    child_id, headers = parent_and_child()
    state = advance_pedagogical_state(None, None, is_opening_turn=True)
    state.update({
        "current_phase": "WORKED_EXAMPLE_3",
        "worked_examples_completed": 2,
        "worked_examples_delivered": {"1": True, "2": True, "3": False},
        "pending_delivery_token": "delivery-token",
        "pending_delivery_phase": "WORKED_EXAMPLE_3",
    })
    db = SessionLocal()
    try:
        db.add(LessonSession(
            child_id=child_id, lesson_id=1, day_number=1,
            pedagogical_state=state, messages=[], is_completed=False,
        ))
        db.commit()
    finally:
        db.close()

    guidance = {"tutor_reply": "Now check your understanding. How many stars are there?", "speech_text": "How many stars are there?"}
    with patch("backend.routers.lessons.get_tutor_response", new=AsyncMock(return_value=guidance)):
        response = client.post("/api/lessons/chat-guidance", headers=headers, json={
            "child_id": child_id, "lesson_id": 1, "day_number": 1, "current_tab": 0,
            "event_type": "teacher_delivery_completed", "delivery_token": "delivery-token",
            "message_history": [],
        })
    assert response.status_code == 200, response.text
    state_after = response.json()["pedagogical_state"]
    assert state_after["active_question"] == "How many fingers do you have on one hand?"
    assert state_after["active_task"] == state_after["active_question"]
    assert state_after["active_phase"] == "UNDERSTANDING_CHECK"
    assert state_after["active_expected_concept"]

    original_question = state_after["active_question"]
    repeat_guidance = {"tutor_reply": "Could you answer a different question?", "speech_text": "Could you answer a different question?"}
    with patch("backend.routers.lessons.get_tutor_response", new=AsyncMock(return_value=repeat_guidance)):
        repeated = client.post("/api/lessons/chat-guidance", headers=headers, json={
            "child_id": child_id, "lesson_id": 1, "day_number": 1, "current_tab": 0,
            "user_prompt": "Repeat that, please", "message_history": [],
        })
    assert repeated.status_code == 200
    repeated_state = repeated.json()["pedagogical_state"]
    assert repeated_state["active_question"] == original_question
    assert repeated_state["remediation_count"] == state_after["remediation_count"]


def test_partial_answers_cannot_advance_independent_academic_phases():
    partial_claiming_advance = {
        "result": "partially_correct",
        "can_advance": True,
        "guided_contribution_sufficient": True,
    }
    phase_status = {
        "UNDERSTANDING_CHECK": "understanding_check_status",
        "APPLICATION": "application_status",
        "MASTERY_CHECK": "mastery_status",
    }
    for phase, status_key in phase_status.items():
        state = advance_pedagogical_state(None, None, is_opening_turn=True)
        state["current_phase"] = phase
        state[status_key] = "pending" if phase != "MASTERY_CHECK" else "in_progress"
        updated = advance_pedagogical_state(state, "A partial answer", eval_result=partial_claiming_advance)
        assert updated["current_phase"] == phase
        assert updated.get("practice_ready") is False
        assert updated.get("mastery_status") != "mastered"


def test_worked_examples_require_explicit_teacher_delivery_completion():
    state = advance_pedagogical_state(None, None, is_opening_turn=True)
    state = advance_pedagogical_state(state, "I am ready")
    assert state["current_phase"] == "TEACHING"

    unchanged = advance_pedagogical_state(state, "I said something arbitrary")
    assert unchanged["current_phase"] == "TEACHING"
    assert unchanged["worked_examples_completed"] == 0

    state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    assert state["current_phase"] == "WORKED_EXAMPLE_1"
    state = advance_pedagogical_state(state, "A micro interaction")
    assert state["current_phase"] == "WORKED_EXAMPLE_1"
    assert state["worked_examples_completed"] == 0

    state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    assert state["worked_examples_delivered"]["1"] is True
    assert state["worked_examples_completed"] == 1


def test_student_greeting_starts_scheduled_teaching_without_a_proceed_turn():
    child_id, headers = parent_and_child()
    guidance = {
        "tutor_reply": "Good morning! Today we are learning Counting to 5. Where have you seen numbers at home?",
        "speech_text": "Good morning! Today we are learning Counting to 5. Where have you seen numbers at home?",
    }
    with patch("backend.routers.lessons.get_tutor_response", new=AsyncMock(return_value=guidance)):
        response = client.post("/api/lessons/chat-guidance", headers=headers, json={
            "child_id": child_id,
            "lesson_id": 1,
            "day_number": 1,
            "current_tab": 0,
            "user_prompt": "Good morning",
            "message_history": [],
        })

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["pedagogical_state"]["current_phase"] == "TEACHING"
    assert payload["requires_delivery_confirmation"] is True
    assert payload["delivery_token"]


def test_later_greeting_does_not_reset_an_in_progress_lesson():
    child_id, headers = parent_and_child()
    state = advance_pedagogical_state(None, None, is_opening_turn=True)
    state["current_phase"] = "WORKED_EXAMPLE_2"
    db = SessionLocal()
    try:
        db.add(LessonSession(
            child_id=child_id, lesson_id=1, day_number=1,
            pedagogical_state=state, messages=[], is_completed=False,
        ))
        db.commit()
    finally:
        db.close()

    guidance = {"tutor_reply": "Hello again. Let us continue.", "speech_text": "Hello again. Let us continue."}
    with patch("backend.routers.lessons.get_tutor_response", new=AsyncMock(return_value=guidance)):
        response = client.post("/api/lessons/chat-guidance", headers=headers, json={
            "child_id": child_id, "lesson_id": 1, "day_number": 1,
            "current_tab": 0, "user_prompt": "hello", "message_history": [],
        })

    assert response.status_code == 200, response.text
    assert response.json()["pedagogical_state"]["current_phase"] == "WORKED_EXAMPLE_2"


def test_pending_evidence_is_saved_without_progress_or_xp():
    child_id, headers = parent_and_child()
    db = SessionLocal()
    try:
        starting_xp = db.query(Child).filter(Child.id == child_id).one().xp
    finally:
        db.close()

    pending = {
        "score": None,
        "verified": False,
        "mastery_status": "pending_review",
        "ai_feedback": "Saved for review.",
        "recommended_action": "retry_evaluation",
    }
    with patch("backend.routers.evidence.evaluate_student_work", new=AsyncMock(return_value=pending)):
        response = client.post("/api/evidence/submit", headers=headers, data={
            "child_id": str(child_id), "lesson_id": "1", "day_number": "1",
            "subject": "Mathematics", "lesson_title": "Counting to 5",
            "skill": "Count accurately", "content": "My work",
        })
    assert response.status_code == 200, response.text
    assert response.json()["verified"] is False
    assert response.json()["score"] is None

    db = SessionLocal()
    try:
        assert db.query(LearningEvidence).filter_by(child_id=child_id).count() == 1
        assert db.query(StudentProgress).filter_by(child_id=child_id, lesson_id=1, day_number=1).first() is None
        assert db.query(Child).filter(Child.id == child_id).one().xp == starting_xp
    finally:
        db.close()
