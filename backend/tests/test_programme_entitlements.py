import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.database import get_db
from backend.models import (
    Child,
    ChildSubject,
    LearningEvidence,
    Lesson,
    LessonDay,
    StudentProgress,
    Subject,
    Unit,
    User,
)
from backend.routers.auth import authorize_child_lesson, authorize_lesson_for_user, get_current_user
from backend.routers.curriculum import router as curriculum_router
from backend.routers.evidence import router as evidence_router
from backend.routers.lessons import router as lessons_router
from backend.routers.parent import get_parent_dashboard
from backend.routers.student import get_student_dashboard
from backend.routers.voice import router as voice_router


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _curriculum(db):
    maths = Subject(title="Mathematics", slug="mathematics")
    bible = Subject(title="Understanding The Word", slug="understanding-the-word")
    db.add_all([maths, bible])
    db.flush()
    maths_unit = Unit(subject_id=maths.id, title="Numbers", order_num=1)
    bible_unit = Unit(subject_id=bible.id, title="The Word", order_num=1)
    db.add_all([maths_unit, bible_unit])
    db.flush()
    maths_lesson = Lesson(
        unit_id=maths_unit.id, title="Counting", level=0, order_num=1,
        learn_content="Count concrete objects.",
    )
    bible_lesson = Lesson(
        unit_id=bible_unit.id, title="God's Word", level=0, order_num=1,
        learn_content="Learn from the Bible.",
    )
    db.add_all([maths_lesson, bible_lesson])
    db.commit()
    return maths, bible, maths_lesson, bible_lesson


def _family(db, programme="homeschool"):
    parent = User(
        email=f"{programme}@example.com",
        name="Parent",
        password_hash="not-used",
        role="parent",
        programme=programme,
    )
    student = User(
        email=f"student-{programme}@example.com",
        name="Child",
        password_hash="not-used",
        role="student",
        programme=programme,
    )
    db.add_all([parent, student])
    db.flush()
    child = Child(parent_id=parent.id, user_id=student.id, name="Child", level=0)
    db.add(child)
    db.commit()
    return parent, student, child


def _enroll(db, child, subject):
    db.add(ChildSubject(child_id=child.id, subject_id=subject.id))
    db.commit()


def test_legacy_homeschool_child_can_access_enrolled_lesson(db):
    maths, _, maths_lesson, _ = _curriculum(db)
    parent, student, child = _family(db)
    _enroll(db, child, maths)

    assert authorize_child_lesson(db, parent, child.id, maths_lesson.id)[1].id == maths_lesson.id
    assert authorize_child_lesson(db, student, child.id, maths_lesson.id)[1].id == maths_lesson.id


def test_bible_child_isolated_even_with_invalid_homeschool_enrollment(db):
    maths, bible, maths_lesson, bible_lesson = _curriculum(db)
    parent, _, child = _family(db, "bible_study")
    _enroll(db, child, maths)
    _enroll(db, child, bible)

    with pytest.raises(HTTPException) as denied:
        authorize_child_lesson(db, parent, child.id, maths_lesson.id)
    assert denied.value.status_code == 403
    assert authorize_child_lesson(db, parent, child.id, bible_lesson.id)[1].id == bible_lesson.id


def test_direct_access_requires_subject_enrollment(db):
    _, _, maths_lesson, _ = _curriculum(db)
    parent, _, child = _family(db)

    with pytest.raises(HTTPException) as denied:
        authorize_child_lesson(db, parent, child.id, maths_lesson.id)
    assert denied.value.status_code == 403


def test_direct_lesson_api_denies_bible_account_homeschool_lesson(db):
    maths, _, maths_lesson, _ = _curriculum(db)
    parent, _, child = _family(db, "bible_study")
    _enroll(db, child, maths)
    app = FastAPI()
    app.include_router(curriculum_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: parent

    response = TestClient(app).get(f"/api/curriculum/lessons/{maths_lesson.id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "This lesson is not included in the Bible Study programme"


def test_subject_catalogue_is_programme_scoped_over_http(db):
    maths, bible, _, _ = _curriculum(db)
    bible_parent, _, _ = _family(db, "bible_study")
    homeschool_parent = User(email="catalogue-home@example.com", name="Home", password_hash="x", role="parent")
    admin = User(email="catalogue-admin@example.com", name="Admin", password_hash="x", role="admin")
    db.add_all([homeschool_parent, admin])
    db.commit()
    actor = {"user": bible_parent}
    app = FastAPI()
    app.include_router(curriculum_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: actor["user"]
    client = TestClient(app)

    assert [item["slug"] for item in client.get("/api/curriculum/subjects").json()] == [bible.slug]
    actor["user"] = homeschool_parent
    assert {item["slug"] for item in client.get("/api/curriculum/subjects").json()} == {maths.slug, bible.slug}
    actor["user"] = admin
    assert {item["slug"] for item in client.get("/api/curriculum/subjects").json()} == {maths.slug, bible.slug}


def test_bible_account_is_denied_at_every_homeschool_lesson_http_boundary(db):
    maths, bible, maths_lesson, _ = _curriculum(db)
    parent, _, child = _family(db, "bible_study")
    _enroll(db, child, maths)  # Simulate stale/invalid legacy enrollment.
    _enroll(db, child, bible)
    app = FastAPI()
    for api_router in (curriculum_router, lessons_router, voice_router, evidence_router):
        app.include_router(api_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: parent
    client = TestClient(app)

    calls = [
        client.get(f"/api/curriculum/lessons/{maths_lesson.id}"),
        client.post("/api/lessons/session", json={"child_id": child.id, "lesson_id": maths_lesson.id}),
        client.get(f"/api/lessons/session/{child.id}/{maths_lesson.id}/1"),
        client.post("/api/lessons/chat-guidance", json={"child_id": child.id, "lesson_id": maths_lesson.id, "current_tab": 0}),
        client.post("/api/lessons/realtime-event", json={"child_id": child.id, "lesson_id": maths_lesson.id, "event_type": "student_response", "student_response": "five"}),
        client.post("/api/voice/realtime-session", json={"child_id": child.id, "lesson_id": maths_lesson.id}),
        client.get(f"/api/lessons/{maths_lesson.id}/quiz", params={"child_id": child.id, "day_number": 1}),
        client.post("/api/lessons/submit-quiz", json={"child_id": child.id, "lesson_id": maths_lesson.id, "day_number": 1, "answers": []}),
        client.post("/api/evidence/submit", data={"child_id": child.id, "lesson_id": maths_lesson.id, "day_number": 1, "subject": "Mathematics", "lesson_title": "Counting", "skill": "Count", "submission_type": "text", "content": "work"}),
    ]

    assert [response.status_code for response in calls] == [403] * len(calls)


def test_parent_cannot_access_another_parents_child(db):
    maths, _, maths_lesson, _ = _curriculum(db)
    parent, _, child = _family(db)
    other = User(email="other@example.com", name="Other", password_hash="x", role="parent")
    db.add(other)
    _enroll(db, child, maths)

    with pytest.raises(HTTPException) as denied:
        authorize_child_lesson(db, other, child.id, maths_lesson.id)
    assert denied.value.status_code == 403
    assert authorize_child_lesson(db, parent, child.id, maths_lesson.id)[0].id == child.id


def test_admin_preserves_explicit_cross_programme_access(db):
    _, _, maths_lesson, _ = _curriculum(db)
    _, _, child = _family(db, "bible_study")
    admin = User(email="admin@example.com", name="Admin", password_hash="x", role="admin")
    db.add(admin)
    db.commit()

    assert authorize_child_lesson(db, admin, child.id, maths_lesson.id)[1].id == maths_lesson.id
    assert authorize_lesson_for_user(db, admin, maths_lesson.id).id == maths_lesson.id


def test_bible_dashboard_auto_enrolls_only_understanding_the_word(db):
    maths, bible, _, _ = _curriculum(db)
    parent, _, child = _family(db, "bible_study")

    first = get_student_dashboard(child.id, db, parent)
    second = get_student_dashboard(child.id, db, parent)
    subject_ids = {
        row.subject_id for row in db.query(ChildSubject).filter(ChildSubject.child_id == child.id).all()
    }
    assert subject_ids == {bible.id}
    assert maths.id not in subject_ids
    assert [item["subject"] for item in first["progress_by_subject"]] == ["Understanding The Word"]
    assert [item["subject"] for item in second["progress_by_subject"]] == ["Understanding The Word"]
    assert db.query(ChildSubject).filter(
        ChildSubject.child_id == child.id,
        ChildSubject.subject_id == bible.id,
    ).count() == 1


def test_bible_dashboard_ignores_stale_homeschool_enrollment(db):
    maths, bible, maths_lesson, bible_lesson = _curriculum(db)
    parent, _, child = _family(db, "bible_study")
    _enroll(db, child, maths)

    dashboard = get_student_dashboard(child.id, db, parent)

    assert [item["subject"] for item in dashboard["progress_by_subject"]] == ["Understanding The Word"]
    assert dashboard["today_lesson"]["id"] == bible_lesson.id
    assert dashboard["today_lesson"]["id"] != maths_lesson.id
    assert db.query(ChildSubject).filter(
        ChildSubject.child_id == child.id,
        ChildSubject.subject_id == bible.id,
    ).count() == 1


def test_legacy_homeschool_dashboard_default_remains_idempotent(db):
    maths, _, maths_lesson, _ = _curriculum(db)
    parent, _, child = _family(db)

    first = get_student_dashboard(child.id, db, parent)
    second = get_student_dashboard(child.id, db, parent)

    assert first["today_lesson"]["id"] == maths_lesson.id
    assert second["today_lesson"]["id"] == maths_lesson.id
    assert db.query(ChildSubject).filter(
        ChildSubject.child_id == child.id,
        ChildSubject.subject_id == maths.id,
    ).count() == 1


def test_bible_parent_dashboard_excludes_stale_homeschool_progress_and_evidence(db):
    maths, bible, maths_lesson, bible_lesson = _curriculum(db)
    parent, _, child = _family(db, "bible_study")
    _enroll(db, child, maths)
    _enroll(db, child, bible)
    db.add_all([
        LessonDay(lesson_id=maths_lesson.id, day_number=1, activity_type="Explore", title="Maths", status="published"),
        LessonDay(lesson_id=bible_lesson.id, day_number=1, activity_type="Weekly Lesson", title="Bible", status="published"),
        StudentProgress(child_id=child.id, lesson_id=maths_lesson.id, day_number=1, status="completed"),
        StudentProgress(child_id=child.id, lesson_id=bible_lesson.id, day_number=1, status="completed"),
        LearningEvidence(
            child_id=child.id, lesson_id=maths_lesson.id, day_number=1,
            subject="Mathematics", lesson_title=maths_lesson.title, skill="Count",
            ai_feedback="Maths feedback", verified=True,
        ),
        LearningEvidence(
            child_id=child.id, lesson_id=bible_lesson.id, day_number=1,
            subject=bible.title, lesson_title=bible_lesson.title, skill="Understand",
            ai_feedback="Bible feedback", verified=True,
        ),
        LearningEvidence(
            child_id=child.id, lesson_id=None, day_number=1,
            subject="Science", lesson_title="Unlinked", skill="Observe",
            ai_feedback="Unlinked feedback", verified=True,
        ),
    ])
    db.commit()

    dashboard = get_parent_dashboard(parent.id, db, parent)

    assert dashboard["children"][0]["completed_lessons"] == 1
    assert dashboard["children"][0]["progress_percentage"] == 100
    assert [item.lesson_id for item in dashboard["recent_evidence"]] == [bible_lesson.id]


def test_bible_evidence_requires_authorized_bible_lesson_and_canonicalizes_subject(db, monkeypatch):
    maths, bible, _, bible_lesson = _curriculum(db)
    parent, _, child = _family(db, "bible_study")
    _enroll(db, child, bible)

    async def successful_evaluation(**_kwargs):
        return {
            "score": 90,
            "ai_feedback": "Well done",
            "verified": True,
            "mastery_status": "mastered",
        }

    monkeypatch.setattr("backend.routers.evidence.evaluate_student_work", successful_evaluation)
    app = FastAPI()
    app.include_router(evidence_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: parent
    client = TestClient(app)

    accepted = client.post("/api/evidence/submit", data={
        "child_id": child.id,
        "lesson_id": bible_lesson.id,
        "day_number": 1,
        "subject": maths.title,
        "lesson_title": "Forged maths title",
        "skill": "Understand",
        "submission_type": "text",
        "content": "My answer",
    })
    assert accepted.status_code == 200
    saved = db.query(LearningEvidence).filter(LearningEvidence.id == accepted.json()["id"]).one()
    assert saved.subject == bible.title
    assert saved.lesson_title == bible_lesson.title

    rejected = client.post("/api/evidence/submit", data={
        "child_id": child.id,
        "day_number": 1,
        "subject": maths.title,
        "lesson_title": "Unlinked maths",
        "skill": "Count",
        "submission_type": "text",
        "content": "My answer",
    })
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "Bible Study evidence must be linked to an Understanding The Word lesson"
    assert db.query(LearningEvidence).filter(LearningEvidence.child_id == child.id).count() == 1


def test_homeschool_evidence_submission_remains_backward_compatible(db, monkeypatch):
    _curriculum(db)
    parent, _, child = _family(db)

    async def successful_evaluation(**_kwargs):
        return {
            "score": 80,
            "ai_feedback": "Good work",
            "verified": True,
            "mastery_status": "competent",
        }

    monkeypatch.setattr("backend.routers.evidence.evaluate_student_work", successful_evaluation)
    app = FastAPI()
    app.include_router(evidence_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: parent

    response = TestClient(app).post("/api/evidence/submit", data={
        "child_id": child.id,
        "day_number": 1,
        "subject": "Mathematics",
        "lesson_title": "Family project",
        "skill": "Count",
        "submission_type": "text",
        "content": "My answer",
    })

    assert response.status_code == 200
    assert response.json()["subject"] == "Mathematics"
