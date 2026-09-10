import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models import LessonSession


client = TestClient(app)


def parent_and_child(label="realtime"):
    suffix = uuid.uuid4().hex
    registered = client.post("/api/auth/register", json={
        "name": "Realtime Parent",
        "email": f"{label}.{suffix}@example.com",
        "password": "SecurePassword123!",
        "role": "parent",
    }).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    child = client.post("/api/auth/add-child", headers=headers, json={
        "parent_id": registered["user"]["id"],
        "name": "Realtime Child",
        "age": 7,
        "education_system": "UK",
        "level": 0,
        "subject_ids": [],
        "avatar": "🦁",
    }).json()
    return child["id"], headers


def event(headers, child_id, event_type, **extra):
    return client.post("/api/lessons/realtime-event", headers=headers, json={
        "child_id": child_id,
        "lesson_id": 1,
        "day_number": 1,
        "event_type": event_type,
        **extra,
    })


def test_realtime_delivery_tokens_enforce_all_three_worked_examples():
    child_id, headers = parent_and_child("delivery")
    started = event(headers, child_id, "start_class")
    assert started.status_code == 200, started.text
    data = started.json()
    assert data["pedagogical_state"]["current_phase"] == "GREETING"
    assert "Realtime Child" in data["phase_instruction"]
    assert data["delivery_token"]

    stale = event(headers, child_id, "teacher_delivery_completed", delivery_token="wrong")
    assert stale.status_code == 409

    for expected_phase in ["TEACHING", "WORKED_EXAMPLE_1", "WORKED_EXAMPLE_2", "WORKED_EXAMPLE_3", "UNDERSTANDING_CHECK"]:
        completed = event(
            headers,
            child_id,
            "teacher_delivery_completed",
            delivery_token=data["delivery_token"],
            assistant_response=f"Completed {data['pedagogical_state']['current_phase']}",
        )
        assert completed.status_code == 200, completed.text
        data = completed.json()
        assert data["pedagogical_state"]["current_phase"] == expected_phase

    assert data["pedagogical_state"]["worked_examples_completed"] == 3
    assert data["pedagogical_state"]["practice_ready"] is False


def test_level_zero_teaching_is_concrete_and_does_not_ask_abstract_reflection():
    child_id, headers = parent_and_child("handoff")
    greeting = event(headers, child_id, "start_class").json()
    teaching = event(
        headers,
        child_id,
        "teacher_delivery_completed",
        delivery_token=greeting["delivery_token"],
    ).json()

    assert teaching["pedagogical_state"]["current_phase"] == "TEACHING"
    assert "model the counting yourself" in teaching["phase_instruction"]
    assert "Do not ask abstract reflection questions" in teaching["phase_instruction"]
    assert "three examples" in teaching["phase_instruction"]
    assert "Never produce a standalone acknowledgement" in teaching["phase_instruction"]


def test_realtime_clarification_preserves_active_question_without_evaluation():
    child_id, headers = parent_and_child("clarification")
    started = event(headers, child_id, "start_class").json()
    data = started
    for _ in range(5):
        data = event(
            headers,
            child_id,
            "teacher_delivery_completed",
            delivery_token=data["delivery_token"],
        ).json()

    registered = event(
        headers,
        child_id,
        "assistant_response_completed",
        assistant_response="How many fingers are on one hand?",
    )
    original = registered.json()["pedagogical_state"]
    with patch("backend.routers.lessons.evaluate_academic_response", new=AsyncMock()) as evaluator:
        clarified = event(
            headers,
            child_id,
            "academic_response",
            student_response="Wait, repeat that please",
        )
    assert clarified.status_code == 200, clarified.text
    state = clarified.json()["pedagogical_state"]
    assert state["current_phase"] == "UNDERSTANDING_CHECK"
    assert state["active_question"] == original["active_question"]
    assert state["remediation_count"] == original["remediation_count"]
    evaluator.assert_not_awaited()


def test_realtime_evaluation_failure_cannot_advance_mastery():
    child_id, headers = parent_and_child("failclosed")
    db = SessionLocal()
    try:
        db.add(LessonSession(
            child_id=child_id,
            lesson_id=1,
            day_number=1,
            pedagogical_state={
                "current_phase": "MASTERY_CHECK",
                "worked_examples_required": 3,
                "worked_examples_completed": 3,
                "worked_examples_delivered": {"1": True, "2": True, "3": True},
                "mastery_status": "in_progress",
                "remediation_count": 0,
                "active_question": "How many fingers are on one hand?",
                "active_task": "How many fingers are on one hand?",
                "active_expected_concept": "Counting to 5",
                "active_phase": "MASTERY_CHECK",
                "practice_ready": False,
            },
            messages=[],
            is_completed=False,
        ))
        db.commit()
    finally:
        db.close()

    with patch("backend.routers.lessons.evaluate_academic_response", new=AsyncMock(return_value=None)):
        response = event(
            headers,
            child_id,
            "academic_response",
            student_response="Five",
        )
    assert response.status_code == 200, response.text
    state = response.json()["pedagogical_state"]
    assert state["current_phase"] == "MASTERY_CHECK"
    assert state["mastery_status"] != "mastered"
    assert state["practice_ready"] is False


def test_realtime_event_enforces_child_ownership_and_day_isolation():
    child_a, headers_a = parent_and_child("owner-a")
    child_b, _ = parent_and_child("owner-b")
    assert event(headers_a, child_b, "start_class").status_code == 403

    assert event(headers_a, child_a, "start_class").status_code == 200
    second_day = client.post("/api/lessons/realtime-event", headers=headers_a, json={
        "child_id": child_a,
        "lesson_id": 1,
        "day_number": 2,
        "event_type": "start_class",
    })
    assert second_day.status_code == 200, second_day.text
    db = SessionLocal()
    try:
        assert db.query(LessonSession).filter_by(child_id=child_a, lesson_id=1).count() == 2
    finally:
        db.close()


def test_complete_realtime_lesson_progresses_deterministically_to_practice_ready():
    child_id, headers = parent_and_child("complete-progression")
    data = event(headers, child_id, "start_class").json()

    expected = ["TEACHING", "WORKED_EXAMPLE_1", "WORKED_EXAMPLE_2", "WORKED_EXAMPLE_3", "UNDERSTANDING_CHECK"]
    seen_tokens = set()
    for next_phase in expected:
        token = data["delivery_token"]
        assert token and token not in seen_tokens
        seen_tokens.add(token)
        response = event(headers, child_id, "teacher_delivery_completed", delivery_token=token)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["pedagogical_state"]["current_phase"] == next_phase

        duplicate = event(headers, child_id, "teacher_delivery_completed", delivery_token=token)
        assert duplicate.status_code == 409

    state = data["pedagogical_state"]
    assert state["worked_examples_completed"] == 3
    assert state["worked_examples_delivered"] == {"1": True, "2": True, "3": True}
    assert state["active_question"] == "What number comes after four when we count to five?"
    assert state["active_phase"] == "UNDERSTANDING_CHECK"
    assert state["active_task"] == state["active_question"]
    assert state["practice_ready"] is False
    assert state["active_question"] in data["phase_instruction"]

    question = event(headers, child_id, "assistant_response_completed", assistant_response="If we count one, two, three, four, what number comes next?")
    assert question.status_code == 200, question.text
    data = question.json()
    assert data["pedagogical_state"]["active_question"] == "What number comes after four when we count to five?"

    with patch("backend.routers.lessons.evaluate_academic_response", new=AsyncMock(return_value={"result": "correct", "feedback": "Correct"})):
        for phase, answer, next_phase, next_question in [
            ("UNDERSTANDING_CHECK", "Five", "GUIDED_PRACTICE", "Count four counters and one more. How many are there?"),
            ("GUIDED_PRACTICE", "Five", "APPLICATION", "You have three books and add two. How many books altogether?"),
            ("APPLICATION", "Five", "MASTERY_CHECK", "What number comes immediately before five?"),
            ("MASTERY_CHECK", "Four", "LESSON_SUMMARY", None),
        ]:
            assert data["pedagogical_state"]["current_phase"] == phase
            response = event(headers, child_id, "academic_response", student_response=answer)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["pedagogical_state"]["current_phase"] == next_phase
            if next_question:
                prompt = event(headers, child_id, "assistant_response_completed", assistant_response=next_question)
                assert prompt.status_code == 200, prompt.text
                data = prompt.json()

    assert data["practice_ready"] is False
    summary_token = data["delivery_token"]
    completed = event(headers, child_id, "teacher_delivery_completed", delivery_token=summary_token)
    assert completed.status_code == 200, completed.text
    final = completed.json()
    assert final["pedagogical_state"]["current_phase"] == "PRACTICE_READY"
    assert final["practice_ready"] is True
