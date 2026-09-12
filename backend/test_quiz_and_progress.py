import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.models import Child, LessonSession, QuizAttempt, StudentProgress
from backend.database import SessionLocal

client = TestClient(app)

def make_ready(child_id, lesson_id=1, day_number=1):
    db = SessionLocal()
    try:
        session = db.query(LessonSession).filter_by(
            child_id=child_id, lesson_id=lesson_id, day_number=day_number
        ).first()
        if not session:
            session = LessonSession(child_id=child_id, lesson_id=lesson_id, day_number=day_number, messages=[])
            db.add(session)
        session.pedagogical_state = {"current_phase": "PRACTICE_READY", "practice_ready": True}
        session.is_completed = True
        db.commit()
    finally:
        db.close()

def test_authoritative_voice_config():
    """Verify a server-side ElevenLabs voice ID is configured without pinning a retired voice."""
    assert settings.ELEVENLABS_VOICE_ID
    assert len(settings.ELEVENLABS_VOICE_ID) >= 10

def test_quiz_grading_all_score_combinations():
    """Test 0/3, 1/3, 2/3, and 3/3 deterministic grading on lesson 1."""
    # Lesson 1 questions in DB:
    # Q1: "How many stars are here: ⭐ ⭐ ⭐?" -> "3"
    # Q2: "Which number comes directly after 4?" -> "5"
    # Q3: "How many fingers are on one hand?" -> "5"
    
    login = client.post("/api/auth/login", json={"email": "sarah@email.com", "password": "password"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    make_ready(1)
    lesson_res = client.get("/api/lessons/1/quiz", headers=headers, params={"child_id": 1, "day_number": 1})
    assert lesson_res.status_code == 200
    questions = lesson_res.json()
    assert len(questions) == 3
    q1_id = questions[0]["id"]
    q2_id = questions[1]["id"]
    q3_id = questions[2]["id"]

    # 1. Test 0/3 (all incorrect)
    sub_0 = {
        "child_id": 1,
        "lesson_id": 1,
        "answers": [
            {"question_id": q1_id, "selected_answer": "99"},
            {"question_id": q2_id, "selected_answer": "99"},
            {"question_id": q3_id, "selected_answer": "99"}
        ]
    }
    res_0 = client.post("/api/lessons/submit-quiz", json=sub_0, headers=headers)
    assert res_0.status_code == 200
    data_0 = res_0.json()
    assert data_0["score"] == 0
    assert data_0["total_questions"] == 3
    assert data_0["percentage"] == 0
    assert data_0["passed"] is False

    # 2. Test 1/3 (1 correct, 2 incorrect)
    sub_1 = {
        "child_id": 1,
        "lesson_id": 1,
        "answers": [
            {"question_id": q1_id, "selected_answer": questions[0]["correct_answer"]},
            {"question_id": q2_id, "selected_answer": "99"},
            {"question_id": q3_id, "selected_answer": "99"}
        ]
    }
    res_1 = client.post("/api/lessons/submit-quiz", json=sub_1, headers=headers)
    assert res_1.status_code == 200
    data_1 = res_1.json()
    assert data_1["score"] == 1
    assert data_1["total_questions"] == 3
    assert data_1["percentage"] == 33
    assert data_1["passed"] is False

    # 3. Test 2/3 (2 correct, 1 incorrect)
    sub_2 = {
        "child_id": 1,
        "lesson_id": 1,
        "answers": [
            {"question_id": q1_id, "selected_answer": questions[0]["correct_answer"]},
            {"question_id": q2_id, "selected_answer": questions[1]["correct_answer"]},
            {"question_id": q3_id, "selected_answer": "99"}
        ]
    }
    res_2 = client.post("/api/lessons/submit-quiz", json=sub_2, headers=headers)
    assert res_2.status_code == 200
    data_2 = res_2.json()
    assert data_2["score"] == 2
    assert data_2["total_questions"] == 3
    assert data_2["percentage"] == 66
    assert data_2["passed"] is True

    # 4. Test 3/3 (all 3 correct)
    sub_3 = {
        "child_id": 1,
        "lesson_id": 1,
        "answers": [
            {"question_id": q1_id, "selected_answer": questions[0]["correct_answer"]},
            {"question_id": q2_id, "selected_answer": questions[1]["correct_answer"]},
            {"question_id": q3_id, "selected_answer": questions[2]["correct_answer"]}
        ]
    }
    res_3 = client.post("/api/lessons/submit-quiz", json=sub_3, headers=headers)
    assert res_3.status_code == 200
    data_3 = res_3.json()
    assert data_3["score"] == 3
    assert data_3["total_questions"] == 3
    assert data_3["percentage"] == 100
    assert data_3["passed"] is True

def test_quiz_and_evidence_immediate_progress_sync():
    """Verify quiz & evidence completion updates student and parent dashboards synchronously."""
    # 1. Create a clean child
    import uuid
    uid = uuid.uuid4().hex[:6]
    parent_res = client.post("/api/auth/register", json={
        "name": f"Parent {uid}",
        "email": f"parent.{uid}@example.com",
        "password": "password123",
        "role": "parent"
    })
    token = parent_res.json()["access_token"]
    parent_id = parent_res.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    child_res = client.post("/api/auth/add-child", json={
        "parent_id": parent_id,
        "name": f"Student {uid}",
        "age": 5,
        "education_system": "UK",
        "level": 0,
        "avatar": "🦁",
        "subject_ids": []
    }, headers=headers)
    child_id = child_res.json()["id"]

    # Check initial student dashboard (progress should be 0%)
    dash_init = client.get(f"/api/student/dashboard/{child_id}", headers=headers).json()
    math_init = next(s for s in dash_init["progress_by_subject"] if s["subject"] == "Mathematics")
    assert math_init["percentage"] == 0

    # Submit 3/3 quiz
    make_ready(child_id)
    qs = client.get(
        "/api/lessons/1/quiz", headers=headers,
        params={"child_id": child_id, "day_number": 1}
    ).json()
    sub_payload = {
        "child_id": child_id,
        "lesson_id": 1,
        "answers": [
            {"question_id": q["id"], "selected_answer": q["correct_answer"]} for q in qs
        ]
    }
    quiz_post = client.post("/api/lessons/submit-quiz", json=sub_payload, headers=headers)
    assert quiz_post.status_code == 200
    assert quiz_post.json()["score"] == 3
    assert quiz_post.json()["percentage"] == 100

    # Check student dashboard immediately (progress should now be 50% for 1 of 2 lessons completed)
    dash_after = client.get(f"/api/student/dashboard/{child_id}", headers=headers).json()
    math_after = next(s for s in dash_after["progress_by_subject"] if s["subject"] == "Mathematics")
    assert math_after["percentage"] == 50

    # Check parent dashboard immediately
    p_dash_after = client.get(f"/api/parent/dashboard/{parent_id}", headers=headers).json()
    c_entry = next(c for c in p_dash_after["children"] if c["id"] == child_id)
    assert c_entry["progress_percentage"] > 0


def test_quiz_attempt_snapshot_idempotency_and_real_retake():
    import uuid
    uid = uuid.uuid4().hex[:8]
    parent = client.post("/api/auth/register", json={
        "name": f"Attempt Parent {uid}", "email": f"attempt.{uid}@example.com",
        "password": "password123", "role": "parent",
    }).json()
    headers = {"Authorization": f"Bearer {parent['access_token']}"}
    child_id = client.post("/api/auth/add-child", headers=headers, json={
        "parent_id": parent["user"]["id"], "name": "Attempt Child", "age": 5,
        "education_system": "UK", "level": 0, "avatar": "🦁", "subject_ids": [],
    }).json()["id"]
    make_ready(child_id)
    questions = client.get("/api/lessons/1/quiz", headers=headers, params={
        "child_id": child_id, "day_number": 1,
    }).json()
    first_id = str(uuid.uuid4())
    payload = {
        "submission_id": first_id, "child_id": child_id, "lesson_id": 1, "day_number": 1,
        "answers": [
            {"question_id": q["id"], "selected_answer": q["correct_answer"]} for q in questions
        ] + [{"question_id": 999999999, "selected_answer": "invalid"}],
    }
    first = client.post("/api/lessons/submit-quiz", headers=headers, json=payload)
    duplicate = client.post("/api/lessons/submit-quiz", headers=headers, json=payload)
    assert first.status_code == 200 and duplicate.status_code == 200
    assert first.json() == duplicate.json()
    assert first.json()["submission_id"] == first_id

    db = SessionLocal()
    try:
        attempt = db.query(QuizAttempt).filter_by(submission_id=first_id).one()
        xp_after_first = db.get(Child, child_id).xp
        assert attempt.correct_count == len(questions)
        assert attempt.total_questions == len(questions)
        assert len(attempt.submitted_answers) == len(questions)
        assert all(set(item) == {"question_id", "selected_answer", "correct_answer", "is_correct"} for item in attempt.submitted_answers)
    finally:
        db.close()

    retake_payload = dict(payload, submission_id=str(uuid.uuid4()))
    retake = client.post("/api/lessons/submit-quiz", headers=headers, json=retake_payload)
    assert retake.status_code == 200 and retake.json()["attempt_id"] != first.json()["attempt_id"]
    assert retake.json()["xp_earned"] == 0
    db = SessionLocal()
    try:
        assert db.query(QuizAttempt).filter_by(child_id=child_id, lesson_id=1, day_number=1).count() == 2
        assert db.get(Child, child_id).xp == xp_after_first
        original = db.query(QuizAttempt).filter_by(submission_id=first_id).one()
        original_score = original.score_percentage
        progress = db.query(StudentProgress).filter_by(child_id=child_id, lesson_id=1, day_number=1).one()
        progress.quiz_score = 17
        db.commit()
        db.refresh(original)
        assert original.score_percentage == original_score
    finally:
        db.close()


@pytest.mark.parametrize("failure_target", ["_update_quiz_progress", "_award_quiz_xp"])
def test_quiz_attempt_progress_and_xp_failures_roll_back_atomically(failure_target):
    import uuid
    uid = uuid.uuid4().hex[:8]
    parent = client.post("/api/auth/register", json={
        "name": f"Rollback Parent {uid}", "email": f"rollback.{uid}@example.com",
        "password": "password123", "role": "parent",
    }).json()
    headers = {"Authorization": f"Bearer {parent['access_token']}"}
    child_id = client.post("/api/auth/add-child", headers=headers, json={
        "parent_id": parent["user"]["id"], "name": "Rollback Child", "age": 5,
        "education_system": "UK", "level": 0, "avatar": "🦁", "subject_ids": [],
    }).json()["id"]
    make_ready(child_id)
    questions = client.get("/api/lessons/1/quiz", headers=headers, params={
        "child_id": child_id, "day_number": 1,
    }).json()
    submission_id = str(uuid.uuid4())
    payload = {
        "submission_id": submission_id, "child_id": child_id, "lesson_id": 1, "day_number": 1,
        "answers": [{"question_id": q["id"], "selected_answer": q["correct_answer"]} for q in questions],
    }
    with patch(f"backend.routers.lessons.{failure_target}", side_effect=RuntimeError("forced failure")):
        with pytest.raises(RuntimeError, match="forced failure"):
            client.post("/api/lessons/submit-quiz", headers=headers, json=payload)

    db = SessionLocal()
    try:
        assert db.query(QuizAttempt).filter_by(submission_id=submission_id).count() == 0
        assert db.query(StudentProgress).filter_by(child_id=child_id, lesson_id=1, day_number=1).count() == 0
        assert db.get(Child, child_id).xp == 0
    finally:
        db.close()
