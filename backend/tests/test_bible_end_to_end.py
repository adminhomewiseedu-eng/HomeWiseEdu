from fastapi.testclient import TestClient

from backend.models import Lesson, LessonDay, Subject, Unit, User
from backend.routers.curriculum import router as curriculum_router
from backend.routers.student import router as student_router
from backend.tests.test_bible_registration_onboarding import api


def test_bible_registration_onboarding_login_dashboard_and_published_lesson(api):
    client, db, actor = api
    client.app.include_router(student_router)
    client.app.include_router(curriculum_router)
    bible = Subject(title="Understanding The Word", slug="understanding-the-word", icon="✝️", color="#FBBF24")
    db.add(bible)
    db.flush()
    unit = Unit(subject_id=bible.id, level=0, title="Knowing God's Word", order_num=1)
    db.add(unit)
    db.flush()
    lesson = Lesson(
        unit_id=unit.id, level=0, title="God Speaks Through His Word", topic="God's Word",
        order_num=1, learn_content="The Bible teaches us truth.", objectives=["Know that the Bible is God's Word"],
    )
    db.add(lesson)
    db.flush()
    db.add(LessonDay(
        lesson_id=lesson.id, day_number=1, activity_type="Weekly Lesson",
        title="God Speaks Through His Word", status="published",
        learning_objectives=["Know that the Bible is God's Word"], key_concept="God speaks through Scripture.",
    ))
    db.commit()

    registration = client.post("/api/auth/register/bible-study", json={
        "name": "Stage Four Parent", "email": "stage4-parent@example.test", "password": "SecureBible123!",
    })
    assert registration.status_code == 200
    actor["user"] = db.query(User).filter(User.email == "stage4-parent@example.test").one()
    parent_headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    created = client.post("/api/auth/add-child", headers=parent_headers, json={
        "name": "Stage Four Child", "age": 6, "education_system": "UK", "level": 0,
        "student_email": "stage4-child@example.test", "student_password": "StudentBible123!",
    })
    assert created.status_code == 200, created.text
    child_id = created.json()["id"]

    parent_dashboard = client.get(f"/api/parent/dashboard/{registration.json()['user']['id']}", headers=parent_headers)
    assert parent_dashboard.status_code == 200
    assert [child["id"] for child in parent_dashboard.json()["children"]] == [child_id]

    student_login = client.post("/api/auth/login", json={
        "email": "stage4-child@example.test", "password": "StudentBible123!",
    })
    assert student_login.status_code == 200
    assert student_login.json()["user"]["programme"] == "bible_study"
    actor["user"] = db.query(User).filter(User.email == "stage4-child@example.test").one()
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    dashboard = client.get(f"/api/student/dashboard/{child_id}", headers=student_headers)
    assert dashboard.status_code == 200
    assert [item["subject"] for item in dashboard.json()["progress_by_subject"]] == ["Understanding The Word"]
    assert dashboard.json()["today_lesson"]["id"] == lesson.id
    detail = client.get(f"/api/curriculum/lessons/{lesson.id}", headers=student_headers)
    assert detail.status_code == 200
    assert detail.json()["title"] == lesson.title


def test_bible_dashboard_has_safe_empty_state_when_level_has_no_published_curriculum(api):
    client, db, actor = api
    client.app.include_router(student_router)
    db.add(Subject(title="Understanding The Word", slug="understanding-the-word", icon="✝️", color="#FBBF24"))
    db.commit()
    registration = client.post("/api/auth/register/bible-study", json={
        "name": "Empty Parent", "email": "empty-parent@example.test", "password": "SecureBible123!",
    })
    actor["user"] = db.query(User).filter(User.email == "empty-parent@example.test").one()
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    created = client.post("/api/auth/add-child", headers=headers, json={"name": "Empty Child", "age": 12, "level": 7})
    dashboard = client.get(f"/api/student/dashboard/{created.json()['id']}", headers=headers)

    assert dashboard.status_code == 200
    assert dashboard.json()["today_lesson"] is None
    assert dashboard.json()["curriculum_state"] == "no_published_lessons"
