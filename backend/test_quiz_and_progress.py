import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.models import QuizQuestion

client = TestClient(app)

def test_authoritative_voice_config():
    """Verify configured voice ID is authoritative and matches client specification."""
    assert settings.ELEVENLABS_VOICE_ID == "cyD08lEy76q03ER1jZ7y"

def test_quiz_grading_all_score_combinations():
    """Test 0/3, 1/3, 2/3, and 3/3 deterministic grading on lesson 1."""
    # Lesson 1 questions in DB:
    # Q1: "How many stars are here: ⭐ ⭐ ⭐?" -> "3"
    # Q2: "Which number comes directly after 4?" -> "5"
    # Q3: "How many fingers are on one hand?" -> "5"
    
    lesson_res = client.get("/api/curriculum/lessons/1")
    assert lesson_res.status_code == 200
    questions = lesson_res.json()["quiz_questions"]
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
    res_0 = client.post("/api/lessons/submit-quiz", json=sub_0)
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
    res_1 = client.post("/api/lessons/submit-quiz", json=sub_1)
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
    res_2 = client.post("/api/lessons/submit-quiz", json=sub_2)
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
    res_3 = client.post("/api/lessons/submit-quiz", json=sub_3)
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
    q_res = client.get("/api/curriculum/lessons/1").json()
    qs = q_res["quiz_questions"]
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
