"""Disposable API coverage for plans, authored weeks and existing learning state."""
import csv
import io
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database import Base, get_db
from backend.models import User, Child, Subject, Unit, Lesson, LessonDay, ChildSubject, StudentProgress, LessonAssignment, LessonSession
from backend.routers.auth import get_current_user
from backend.routers import student, parent, lessons, curriculum
from backend.services.curriculum_importer import import_curriculum_csv_data


@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    users = [User(email=f'{n}@example.test', name=n, role=r, programme=p, password_hash='unused') for n, r, p in
             [('parent', 'parent', 'homeschool'), ('student', 'student', 'homeschool'), ('other', 'parent', 'homeschool'),
              ('bible', 'parent', 'bible_study'), ('admin', 'admin', 'homeschool')]]
    db.add_all(users); db.flush()
    child = Child(parent_id=users[0].id, user_id=users[1].id, name='Child', level=0)
    bible_child = Child(parent_id=users[3].id, name='Bible child', level=0)
    subjects = [Subject(title=t, slug=s) for t, s in [('Mathematics', 'mathematics'), ('English Language', 'english-language'), ('Understanding The Word', 'understanding-the-word')]]
    db.add_all([child, bible_child, *subjects]); db.flush()
    all_lessons = []
    for i, subject in enumerate(subjects):
        unit = Unit(subject_id=subject.id, level=0, title='Unit', order_num=1)
        db.add(unit); db.flush()
        lesson = Lesson(unit_id=unit.id, level=0, title=f'Lesson {i}', order_num=1, learn_content='Existing content', curriculum_week=10 if i == 0 else None)
        db.add(lesson); db.flush()
        db.add_all([LessonDay(lesson_id=lesson.id, day_number=n, title=f'Session {n}', status='published') for n in (1, 2)])
        db.add(ChildSubject(child_id=child.id, subject_id=subject.id))
        all_lessons.append(lesson)
    db.add(ChildSubject(child_id=bible_child.id, subject_id=subjects[2].id)); db.commit()
    app = FastAPI()
    for router in (student.router, parent.router, lessons.router, curriculum.router): app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: users[0]
    with TestClient(app) as client:
        yield db, client, app, users, child, bible_child, all_lessons
    db.close(); engine.dispose()


def payload(lesson, **extra):
    return dict(lesson_id=lesson.id, day_number=1, scheduled_date='2026-11-10', priority=0, **extra)


def test_assign_reschedule_order_cancel_and_preserve_progress(setup):
    db, client, app, users, child, _, ls = setup
    db.add(StudentProgress(child_id=child.id, lesson_id=ls[0].id, day_number=2, status='completed', quiz_score=80))
    db.add(LessonSession(child_id=child.id, lesson_id=ls[0].id, day_number=1, pedagogical_state={'current_phase': 'TEACHING'})); db.commit()
    url = f'/api/parent/children/{child.id}/assignments'
    first = client.post(url, json={**payload(ls[0]), 'priority': 5}).json()['id']
    second = client.post(url, json=payload(ls[1])).json()['id']
    assert client.post(url, json=payload(ls[1])).json()['id'] == second
    assert db.query(LessonAssignment).count() == 2
    assert [a['assignment_id'] for a in client.get(url).json()] == [second, first]
    assert client.patch(f'{url}/{first}', json={'scheduled_date': '2026-11-09', 'priority': 0}).status_code == 200
    assert client.get(url).json()[0]['assignment_id'] == first
    assert client.get(f'/api/student/dashboard/{child.id}').json()['today_lesson']['assignment_id'] == first
    assert client.patch(f'{url}/{first}', json={'cancelled': True}).status_code == 200
    assert len(client.get(url).json()) == 1
    assert db.query(StudentProgress).one().quiz_score == 80
    assert db.query(LessonSession).one().pedagogical_state == {'current_phase': 'TEACHING'}
    assert db.query(Child).filter_by(id=child.id).one().xp == 0


def test_browse_week_ten_and_unknown_without_progress_writes(setup):
    db, client, app, users, child, _, ls = setup
    app.dependency_overrides[get_current_user] = lambda: users[1]
    result = client.get(f'/api/student/{child.id}/lesson-options').json()
    assert {x['curriculum_week'] for x in result['sessions']} == {10, None}
    assert len(result['sessions']) == 6
    assert all(x['unit_id'] for x in result['sessions'])
    assert db.query(StudentProgress).count() == 0
    assert db.query(LessonAssignment).count() == 0
    assert client.get(f'/api/curriculum/lessons/{ls[0].id}').status_code == 200
    assert client.post(f'/api/parent/children/{child.id}/assignments', json=payload(ls[0])).status_code == 403


@pytest.mark.parametrize('invalid', ['level', 'archived', 'draft', 'day', 'enrollment'])
def test_ineligible_assignments_and_direct_sessions_denied(setup, invalid):
    db, client, app, users, child, _, ls = setup
    p = payload(ls[0])
    if invalid == 'level': ls[0].level = 1
    if invalid == 'archived': ls[0].archived = True
    if invalid == 'draft': ls[0].days[0].status = 'pending'
    if invalid == 'day': p['day_number'] = 99
    if invalid == 'enrollment': db.query(ChildSubject).filter_by(child_id=child.id, subject_id=ls[0].unit.subject_id).delete()
    db.commit()
    assert client.post(f'/api/parent/children/{child.id}/assignments', json=p).status_code in (403, 404)
    assert client.get(f'/api/lessons/session/{child.id}/{ls[0].id}/{p["day_number"]}').status_code in (403, 404)
    assert db.query(LessonAssignment).count() == 0


def test_cross_parent_bible_isolation_and_admin(setup):
    db, client, app, users, child, bible_child, ls = setup
    app.dependency_overrides[get_current_user] = lambda: users[2]
    assert client.get(f'/api/student/{child.id}/lesson-options').status_code == 403
    assert client.post(f'/api/parent/children/{child.id}/assignments', json=payload(ls[0])).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: users[3]
    assert client.get(f'/api/student/{bible_child.id}/lesson-options').status_code == 403
    assert client.post(f'/api/parent/children/{bible_child.id}/assignments', json=payload(ls[2])).status_code == 403
    assert client.get(f'/api/student/dashboard/{bible_child.id}').status_code == 200
    app.dependency_overrides[get_current_user] = lambda: users[4]
    assert client.post(f'/api/parent/children/{child.id}/assignments', json=payload(ls[0])).status_code == 200


def test_completed_assignments_derive_status_and_revalidate_entitlements(setup):
    db, client, app, users, child, _, ls = setup
    url = f'/api/parent/children/{child.id}/assignments'
    ident = client.post(url, json=payload(ls[0])).json()['id']
    assert client.delete(f'/api/curriculum/admin/lessons/{ls[0].id}').status_code == 403
    app.dependency_overrides[get_current_user] = lambda: users[4]
    dependencies = client.get(f'/api/curriculum/admin/lessons/{ls[0].id}/dependencies').json()
    assert dependencies['dependencies']['lesson_assignments'] == 1
    assert dependencies['can_delete'] is False
    assert client.delete(f'/api/curriculum/admin/lessons/{ls[0].id}').status_code == 409
    app.dependency_overrides[get_current_user] = lambda: users[0]
    db.add(StudentProgress(child_id=child.id, lesson_id=ls[0].id, day_number=1, status='completed')); db.commit()
    assert client.get(url).json()[0]['status'] == 'completed'
    db.query(ChildSubject).filter_by(child_id=child.id, subject_id=ls[0].unit.subject_id).delete(); db.commit()
    assert client.get(url).json()[0]['available'] is False
    app.dependency_overrides[get_current_user] = lambda: users[1]
    assert client.get(f'/api/student/{child.id}/lesson-options').json()['assignments'] == []
    app.dependency_overrides[get_current_user] = lambda: users[0]
    assert client.get(f'/api/lessons/session/{child.id}/{ls[0].id}/1').status_code == 403
    assert client.patch(f'{url}/{ident}', json={'cancelled': True}).status_code == 200


def test_reschedule_conflict_and_invalid_fields_do_not_change_plan(setup):
    db, client, app, users, child, _, ls = setup
    url = f'/api/parent/children/{child.id}/assignments'
    first = client.post(url, json=payload(ls[0])).json()['id']
    second = client.post(url, json={**payload(ls[0]), 'scheduled_date': '2026-11-11'}).json()['id']
    assert client.patch(f'{url}/{second}', json={'scheduled_date': '2026-11-10'}).status_code == 409
    assert client.patch(f'{url}/{first}', json={'priority': -1}).status_code == 422
    assert client.patch(f'{url}/{first}', json={'scheduled_date': None}).status_code == 422
    assert client.post(url, json={**payload(ls[0]), 'scheduled_date': 'invalid'}).status_code == 422
    assert db.query(LessonAssignment).count() == 2
    assert db.query(LessonAssignment).filter_by(id=second).one().scheduled_date == '2026-11-11'
    assert db.query(StudentProgress).count() == 0
    assert client.patch(f'{url}/{first}', json={'cancelled': True}).status_code == 200
    assert client.patch(f'{url}/{second}', json={'scheduled_date': '2026-11-10'}).status_code == 200
    assert len(client.get(url).json()) == 1
    assert client.post(url, json=payload(ls[0])).json()['id'] == second


def test_parent_can_cancel_after_publication_is_removed(setup):
    db, client, app, users, child, _, ls = setup
    url = f'/api/parent/children/{child.id}/assignments'
    ident = client.post(url, json=payload(ls[0])).json()['id']
    ls[0].days[0].status = 'pending'; db.commit()
    unavailable = client.get(url).json()[0]
    assert unavailable['available'] is False
    assert unavailable['title'] == 'Assignment no longer available'
    assert client.patch(f'{url}/{ident}', json={'priority': 1}).status_code == 404
    assert client.patch(f'{url}/{ident}', json={'cancelled': True}).status_code == 200
    assert db.query(LessonAssignment).filter_by(id=ident).one().cancelled is True


def test_import_authored_week_and_reject_invalid_or_conflicting_week(setup):
    db, *_ = setup
    headers = ['Subject', 'Level', 'Unit_Name', 'Subtopic', 'Lesson Number', 'Lesson Title', 'Lesson Type', 'Learning objectives', 'Key_concept', 'AI_Teaching_Script', 'Status', 'Curriculum Week']
    def source(week):
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=headers); writer.writeheader()
        writer.writerow(dict(zip(headers, ['Mathematics', '0', 'Unit', 'Imported', '9', 'Imported', 'Weekly Lesson', 'Objective', 'Concept', 'Script', 'Pending', week])))
        return output.getvalue()
    import_curriculum_csv_data(source('10'), db); db.flush()
    lesson = db.query(Lesson).filter_by(order_num=9).one()
    assert lesson.curriculum_week == 10
    import_curriculum_csv_data(source(''), db); db.flush()
    assert lesson.curriculum_week == 10
    with pytest.raises(ValueError, match='positive whole number'):
        import_curriculum_csv_data(source('-1'), db)
