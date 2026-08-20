import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.utils.levels import get_level_label, EDUCATION_SYSTEMS

client = TestClient(app)

def demo_headers(email="sarah@email.com"):
    response = client.post("/api/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "HomeWiseEdu" in response.json()["app"]

def test_canonical_levels_mapping():
    # UK Level 0 must be strictly "Reception", never "Year 0"
    assert get_level_label(0, "UK") == "Reception"
    assert get_level_label(1, "UK") == "Year 1"
    assert get_level_label(4, "UK") == "Year 4"
    assert get_level_label(13, "UK") == "Year 13"

    # USA Level 0 must be "Kindergarten"
    assert get_level_label(0, "USA") == "Kindergarten"
    assert get_level_label(1, "USA") == "Grade 1"
    assert get_level_label(4, "USA") == "Grade 4"

    # Australia Level 0 must be "Foundation / Prep"
    assert get_level_label(0, "Australia") == "Foundation / Prep"

    # Canada Level 0 must be "Kindergarten"
    assert get_level_label(0, "Canada") == "Kindergarten"

def test_auth_login():
    response = client.post("/api/auth/login", json={"email": "sarah@email.com", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["name"] == "Sarah Wilson"

def test_curriculum_subjects():
    response = client.get("/api/curriculum/subjects")
    assert response.status_code == 200
    subjects = response.json()
    assert len(subjects) == 12
    titles = [s["title"] for s in subjects]
    assert "Mathematics" in titles
    assert "English Language" in titles
    assert "Science" in titles
    assert "Phonics" in titles
    assert "Understanding The Word" in titles
    assert "Critical Thinking & Logic" in titles

def test_curriculum_importer_csv():
    # Test CSV data matching client blueprint format
    sample_csv = (
        "Level,Subject,Unit,Lesson Topic,Day,Activity Type,Learning Objectives,Key Concept,Bible Reference,Biblical Theme,Biblical Application,Character Reference,Estimated Duration,AI Teaching Script,Real-World Context,Visual Support,Practice Questions,Vocabulary,Reading Recommendations,Status\n"
        "0,Mathematics,Unit 1: Number Sense,Counting to 5,1,Explore,Count up to 5 items|Recognize numbers 1-5,Numbers represent quantity,Psalm 139:14,Care,God knows us,Attentiveness,20 mins,Let's count 5 toys together,Counting toys at home,Five blocks lined up,How many blocks?|Count 5 fingers,Count|Number|Quantity,Counting Fun,active\n"
        "0,Mathematics,Unit 1: Number Sense,Counting to 5,2,Practice,Match 1-5 to dots|Write numerals 1-5,Numerals are symbols,Proverbs 3:5,Order,Order in creation,Patience,20 mins,Let's practice writing 1 to 5,Drawing dot cards,Dot cards 1 to 5,Which number comes after 2?,Numeral|Symbol,Dot Cards,active\n"
        "0,Mathematics,Unit 1: Number Sense,Counting to 5,3,Apply,Solve sharing puzzles up to 5,Counting helps sharing,Galatians 6:9,Generosity,Sharing with siblings,Generosity,25 mins,Let's share 5 apples fairly,Sharing fruit,Two baskets sharing 5 apples,If you share 5 apples,Share|Total,Sharing Fun,active\n"
    )
    response = client.post(
        "/api/curriculum/import-csv",
        files={"file": ("curriculum_test.csv", sample_csv.encode("utf-8"), "text/csv")},
        headers=demo_headers("jake@email.com")
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["stats"]["days_processed"] == 3

def test_parent_dashboard():
    response = client.get("/api/parent/dashboard/1", headers=demo_headers())
    assert response.status_code == 200
    data = response.json()
    assert len(data["children"]) >= 3
    
    # Check Leo (Level 0 UK Reception)
    leo = next((c for c in data["children"] if c["name"] == "Leo"), None)
    assert leo is not None
    assert leo["level"] == 0
    assert leo["level_label"] == "Reception"

    # Check Mayowa (Level 4 UK Year 4)
    mayowa = next((c for c in data["children"] if c["name"] == "Mayowa"), None)
    assert mayowa is not None
    assert mayowa["level"] == 4
    assert mayowa["level_label"] == "Year 4"

def test_leo_level_0_student_dashboard():
    # Find Leo's child ID
    headers = demo_headers()
    parent_res = client.get("/api/parent/dashboard/1", headers=headers)
    leo_id = next(c["id"] for c in parent_res.json()["children"] if c["name"] == "Leo")

    response = client.get(f"/api/student/dashboard/{leo_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Leo"
    assert data["level"] == 0
    assert data["level_label"] == "Reception"
    assert data["today_lesson"] is not None
    assert "Counting to 5" in data["today_lesson"]["title"]
    assert data["today_lesson"]["day_number"] in [1, 2]
    assert data["today_lesson"]["activity_type"] in ["Explore", "Practice"]

def test_lesson_tutor_and_session():
    # Chat guidance with Ms. Ade
    chat_payload = {
        "child_id": 1,
        "lesson_id": 1,
        "current_tab": 0,
        "user_prompt": "What are we learning today?"
    }
    headers = demo_headers()
    response = client.post("/api/lessons/chat-guidance", json=chat_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "tutor_reply" in data
    assert "speech_text" in data

    # Resumable session update & get
    sess_payload = {
        "child_id": 1,
        "lesson_id": 1,
        "day_number": 1,
        "current_tab": 2,
        "messages": [{"sender": "tutor", "text": "Welcome to tab 2!"}]
    }
    s_post = client.post("/api/lessons/session", json=sess_payload, headers=headers)
    assert s_post.status_code == 200

    s_get = client.get("/api/lessons/session/1/1/1", headers=headers)
    assert s_get.status_code == 200
    assert s_get.json()["current_tab"] == 2

def test_evidence_submission():
    # Find Leo
    headers = demo_headers()
    parent_res = client.get("/api/parent/dashboard/1", headers=headers)
    leo_id = next(c["id"] for c in parent_res.json()["children"] if c["name"] == "Leo")

    form_data = {
        "child_id": str(leo_id),
        "lesson_id": "1",
        "day_number": "1",
        "subject": "Mathematics",
        "lesson_title": "Counting to 5",
        "skill": "Count up to 5 items",
        "content": "I counted 5 apples: 1, 2, 3, 4, 5."
    }
    evaluation = {
        "score": 95,
        "verified": True,
        "mastery_status": "mastered",
        "ai_feedback": "Accurate counting evidence.",
    }
    with patch("backend.routers.evidence.evaluate_student_work", new=AsyncMock(return_value=evaluation)):
        response = client.post("/api/evidence/submit", data=form_data, headers=headers)
    assert response.status_code == 200
    ev = response.json()
    assert ev["verified"] is True
    assert ev["score"] >= 80
    assert "ai_feedback" in ev

def test_voice_tts_endpoint():
    tts_payload = {"text": "Hello Leo! Welcome to Counting to 5."}
    response = client.post("/api/voice/tts", json=tts_payload, headers=demo_headers())
    assert response.status_code == 200
    data = response.json()
    assert "success" in data

def test_student_report_endpoint():
    response = client.get("/api/reports/student/1", headers=demo_headers())
    assert response.status_code == 200
    report = response.json()
    assert "student" in report
    assert "academic_pathway" in report
    assert "learning_evidence" in report
    assert "summary" in report

def test_new_parent_signup_and_child_registration_flow():
    import uuid
    unique_suffix = uuid.uuid4().hex[:6]
    # 1. Register a completely new parent
    signup_payload = {
        "name": "David Miller",
        "email": f"david.miller.{unique_suffix}@example.com",
        "password": "securepassword123",
        "role": "parent"
    }
    signup_res = client.post("/api/auth/register", json=signup_payload)
    assert signup_res.status_code == 200
    signup_data = signup_res.json()
    token = signup_data["access_token"]
    parent_id = signup_data["user"]["id"]
    assert signup_data["user"]["name"] == "David Miller"

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register/add a child for David
    child_payload = {
        "parent_id": parent_id,
        "name": "Oliver",
        "age": 5,
        "education_system": "UK",
        "level": 0, # UK Reception
        "avatar": "🦊",
        "subject_ids": []
    }
    add_child_res = client.post("/api/auth/add-child", json=child_payload, headers=headers)
    assert add_child_res.status_code == 200
    child_data = add_child_res.json()
    assert child_data["name"] == "Oliver"
    assert child_data["level"] == 0
    assert child_data["level_label"] == "Reception"
    assert child_data["parent_id"] == parent_id
    oliver_id = child_data["id"]

    # 3. Fetch David's Parent Dashboard
    parent_dash_res = client.get(f"/api/parent/dashboard/{parent_id}", headers=headers)
    assert parent_dash_res.status_code == 200
    dash_data = parent_dash_res.json()
    
    # Verify parent name is David (not Sarah)
    assert dash_data["parent_name"] == "David"
    # Verify children list contains Oliver only (not Leo/Mayowa)
    assert len(dash_data["children"]) == 1
    assert dash_data["children"][0]["name"] == "Oliver"
    assert dash_data["children"][0]["level_label"] == "Reception"

    # 4. Fetch Oliver's Student Dashboard
    student_dash_res = client.get(f"/api/student/dashboard/{oliver_id}", headers=headers)
    assert student_dash_res.status_code == 200
    student_data = student_dash_res.json()
    assert student_data["name"] == "Oliver"
    assert student_data["level"] == 0
    assert student_data["level_label"] == "Reception"
    assert student_data["today_lesson"] is not None
    assert "Counting to 5" in student_data["today_lesson"]["title"]
    assert student_data["today_lesson"]["day_number"] == 1

