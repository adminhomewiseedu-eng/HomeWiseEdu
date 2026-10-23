import io
from pathlib import Path
import shutil

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Child, ChildSubject, Subject, User
from backend.routers.auth import get_current_user, router as auth_router
from backend.routers.parent import router as parent_router


@pytest.fixture()
def api(monkeypatch):
    test_storage = Path(__file__).resolve().parent / ".tmp_bible_profiles"
    test_storage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("backend.config.settings.STORAGE_ROOT", str(test_storage))
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    actor = {"user": None}
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(parent_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: actor["user"]
    try:
        yield TestClient(app), db, actor
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        shutil.rmtree(test_storage, ignore_errors=True)


def _register(client, db, actor, email="bible-parent@example.test", **extra):
    payload = {
        "name": "Bible Parent",
        "email": email,
        "password": "SecureBible123!",
        **extra,
    }
    response = client.post("/api/auth/register/bible-study", json=payload)
    assert response.status_code == 200, response.text
    parent = db.query(User).filter(User.email == email).one()
    actor["user"] = parent
    return response, parent


def _subjects(db, include_bible=True):
    maths = Subject(title="Mathematics", slug="mathematics")
    db.add(maths)
    bible = None
    if include_bible:
        bible = Subject(title="Understanding The Word", slug="understanding-the-word")
        db.add(bible)
    db.commit()
    return maths, bible


def test_bible_registration_is_server_owned_and_uses_normal_session_response(api):
    client, db, actor = api
    response, parent = _register(client, db, actor, programme="homeschool")

    assert parent.programme == "bible_study"
    assert parent.role == "parent"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["user"]["email"] == "bible-parent@example.test"
    assert response.json()["user"]["programme"] == "bible_study"


def test_existing_registration_remains_homeschool_despite_programme_tampering(api):
    client, db, _ = api
    response = client.post("/api/auth/register", json={
        "name": "Homeschool Parent",
        "email": "home-parent@example.test",
        "password": "SecureHome123!",
        "programme": "bible_study",
    })

    assert response.status_code == 200, response.text
    assert db.query(User).filter(User.email == "home-parent@example.test").one().programme == "homeschool"
    assert response.json()["user"]["programme"] == "homeschool"


def test_bible_registration_reuses_duplicate_email_and_parent_role_guards(api):
    client, db, actor = api
    _register(client, db, actor)

    duplicate = client.post("/api/auth/register/bible-study", json={
        "name": "Duplicate",
        "email": " BIBLE-PARENT@example.test ",
        "password": "SecureBible123!",
    })
    invalid_role = client.post("/api/auth/register/bible-study", json={
        "name": "Not Student",
        "email": "student-role@example.test",
        "password": "SecureBible123!",
        "role": "student",
    })

    assert duplicate.status_code == 400
    assert invalid_role.status_code == 403
    assert db.query(User).filter(User.email == "student-role@example.test").count() == 0


def test_bible_child_creation_enrolls_exact_subject_and_student_can_login(api):
    client, db, actor = api
    _, bible = _subjects(db)
    _, parent = _register(client, db, actor)
    response = client.post("/api/auth/add-child", json={
        "name": "Bible Learner",
        "age": 10,
        "date_of_birth": "2016-03-04",
        "education_system": "USA",
        "level": 5,
        "avatar": "🐯",
        "student_email": "bible-student@example.test",
        "student_password": "StudentBible123!",
    })

    assert response.status_code == 200, response.text
    child = db.query(Child).filter(Child.parent_id == parent.id).one()
    student = db.query(User).filter(User.email == "bible-student@example.test").one()
    enrollments = db.query(ChildSubject).filter(ChildSubject.child_id == child.id).all()
    assert (child.age, child.education_system, child.level, child.avatar) == (10, "USA", 5, "🐯")
    assert student.programme == "bible_study"
    assert child.user_id == student.id
    assert [item.subject_id for item in enrollments] == [bible.id]

    login = client.post("/api/auth/login", json={
        "email": "bible-student@example.test",
        "password": "StudentBible123!",
    })
    assert login.status_code == 200, login.text
    assert login.json()["user"]["role"] == "student"
    assert login.json()["user"]["programme"] == "bible_study"
    assert login.json()["user"]["child_id"] == child.id


def test_bible_parent_can_use_existing_private_profile_image_flow(api):
    client, db, actor = api
    _subjects(db)
    _register(client, db, actor)
    created = client.post("/api/auth/add-child", json={"name": "Photo Learner"})
    child_id = created.json()["id"]
    png = b"\x89PNG\r\n\x1a\n" + b"bible-profile-test"

    upload = client.post(
        f"/api/parent/children/{child_id}/profile-image",
        files={"image": ("profile.png", io.BytesIO(png), "image/png")},
    )
    fetched = client.get(f"/api/parent/children/{child_id}/profile-image")

    assert upload.status_code == 200, upload.text
    assert fetched.status_code == 200
    assert fetched.content == png


def test_bible_child_rejects_arbitrary_subject_ids_without_partial_records(api):
    client, db, actor = api
    maths, _ = _subjects(db)
    _, parent = _register(client, db, actor)

    response = client.post("/api/auth/add-child", json={
        "name": "Blocked Learner",
        "subject_ids": [maths.id],
        "student_email": "blocked-student@example.test",
        "student_password": "BlockedStudent123!",
    })

    assert response.status_code == 403
    assert db.query(Child).filter(Child.parent_id == parent.id).count() == 0
    assert db.query(User).filter(User.email == "blocked-student@example.test").count() == 0


def test_missing_bible_subject_fails_before_child_or_student_creation(api):
    client, db, actor = api
    _subjects(db, include_bible=False)
    _, parent = _register(client, db, actor)

    response = client.post("/api/auth/add-child", json={
        "name": "Unconfigured Learner",
        "student_email": "unconfigured@example.test",
        "student_password": "Unconfigured123!",
    })

    assert response.status_code == 503
    assert db.query(Child).filter(Child.parent_id == parent.id).count() == 0
    assert db.query(User).filter(User.email == "unconfigured@example.test").count() == 0


def test_bible_child_edit_and_credentials_cannot_escalate_programme(api):
    client, db, actor = api
    maths, bible = _subjects(db)
    _register(client, db, actor)
    created = client.post("/api/auth/add-child", json={
        "name": "Protected Learner",
        "student_email": "protected@example.test",
        "student_password": "Protected123!",
    })
    child = db.get(Child, created.json()["id"])
    child.login_user.programme = "homeschool"
    db.commit()

    subject_change = client.patch(f"/api/parent/children/{child.id}", json={
        "subject_ids": [maths.id],
    })
    credentials = client.put(f"/api/parent/children/{child.id}/credentials", json={
        "password": "Protected456!",
    })

    assert subject_change.status_code == 403
    assert credentials.status_code == 200
    db.refresh(child.login_user)
    assert child.login_user.programme == "bible_study"
    assert [item.subject_id for item in child.enrolled_subjects] == [bible.id]


def test_cross_parent_cannot_add_or_edit_bible_child(api):
    client, db, actor = api
    _subjects(db)
    _, first_parent = _register(client, db, actor, email="first@example.test")
    child_response = client.post("/api/auth/add-child", json={"name": "First Child"})
    child_id = child_response.json()["id"]
    _, second_parent = _register(client, db, actor, email="second@example.test")

    add_to_first = client.post(
        f"/api/auth/add-child?parent_id={first_parent.id}",
        json={"name": "Injected Child"},
    )
    edit_first = client.patch(f"/api/parent/children/{child_id}", json={"name": "Taken Over"})

    assert actor["user"].id == second_parent.id
    assert add_to_first.status_code == 403
    assert edit_first.status_code == 403
    assert db.get(Child, child_id).name == "First Child"
