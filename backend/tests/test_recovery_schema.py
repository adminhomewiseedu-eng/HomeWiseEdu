"""Synthetic local compatibility tests; no production credentials or data."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import main
from backend.database import Base, get_db
from backend.models import (User, Child, ChildSubject, Subject, Unit, Lesson, LessonDay,
                            StudentProgress, QuizAttempt, LearningEvidence, LessonSession)
from backend.routers.auth import get_password_hash
from backend.services.recovery_schema import schema_is_compatible


def apply_0014(engine):
    """Execute the exact approved migration body, kept inactive as a test fixture."""
    path = Path(__file__).parent / 'fixtures' / '0014_lesson_assignments.py'
    spec = importlib.util.spec_from_file_location('approved_0014_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        # Use this transaction's connection for every real Alembic operation.
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
        connection.execute(sa.text("UPDATE alembic_version SET version_num='0014_lesson_assignments'"))


def make_0013(engine):
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(sa.text('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)'))
        connection.execute(sa.text("INSERT INTO alembic_version VALUES ('0013_programme_entitlements')"))


def history_snapshot(engine, populated):
    tables = ['student_progress', 'quiz_attempts', 'learning_evidence', 'lesson_sessions']
    if populated:
        tables += ['lesson_assignments']
    with engine.connect() as c:
        result = {table: [dict(row) for row in c.execute(sa.text(f'SELECT * FROM {table} ORDER BY id')).mappings()]
                  for table in tables}
        if populated:
            result['weeks'] = list(c.execute(sa.text('SELECT id,curriculum_week FROM lessons WHERE curriculum_week IS NOT NULL ORDER BY id')))
        return json.dumps(result, default=str, sort_keys=True)


def exercise_recovery(engine, revision, populated=False, migrate=None):
    """Shared SQLite and real PostgreSQL integration contract."""
    make_0013(engine)
    if revision == '0014':
        (migrate or apply_0014)(engine)
    factory = sessionmaker(bind=engine)
    password = 'DisposableRecovery123!'
    hashed = get_password_hash(password)
    with factory() as db:
        families = []
        lessons = []
        for programme, title, slug in [('homeschool', 'Mathematics', 'mathematics'),
                                       ('bible_study', 'Understanding The Word', 'understanding-the-word')]:
            parent = User(email=f'{programme}-parent@example.test', name='Local Parent', role='parent',
                          programme=programme, password_hash=hashed)
            student = User(email=f'{programme}-student@example.test', name='Local Student', role='student',
                           programme=programme, password_hash=hashed)
            subject = Subject(title=title, slug=slug)
            db.add_all([parent, student, subject]); db.flush()
            child = Child(parent_id=parent.id, user_id=student.id, name='Local Child', age=6, level=0, xp=100)
            unit = Unit(subject_id=subject.id, title='Number Sense' if programme == 'homeschool' else 'Scripture', level=0)
            db.add_all([child, unit]); db.flush()
            lesson = Lesson(unit_id=unit.id, title='Local Lesson', topic='Counting' if programme == 'homeschool' else 'Scripture',
                            level=0, order_num=1, learn_content='Synthetic test only')
            db.add(lesson); db.flush()
            db.add_all([ChildSubject(child_id=child.id, subject_id=subject.id),
                        LessonDay(lesson_id=lesson.id, day_number=1, title='Local Session',
                                  activity_type='Weekly Lesson', status='published'),
                        StudentProgress(child_id=child.id, lesson_id=lesson.id, day_number=1,
                                        status='completed', quiz_score=80, quiz_xp_awarded=True),
                        QuizAttempt(submission_id='local-'+programme, child_id=child.id, lesson_id=lesson.id,
                                    day_number=1, score_percentage=80, correct_count=4, total_questions=5,
                                    submitted_answers=[{'selected_answer':'Synthetic'}], passed=True, xp_earned=10),
                        LessonSession(child_id=child.id, lesson_id=lesson.id, day_number=1,
                                      pedagogical_state={'current_phase':'PRACTICE_READY'}),
                        LearningEvidence(child_id=child.id, lesson_id=lesson.id, subject=title,
                                         lesson_title='Local Lesson', skill='Local skill', ai_feedback='Synthetic')])
            families.append(dict(programme=programme,parent_id=parent.id,student_id=student.id,child_id=child.id,lesson_id=lesson.id))
            lessons.append(lesson.id)
        admin = User(email='local-admin@example.test', name='Local Admin', role='admin', password_hash=hashed)
        db.add(admin)
        extra = [Lesson(unit_id=1, level=0, title=name, learn_content='Synthetic', order_num=index+2)
                 for index,name in enumerate(('Assigned only','Authored week only','Unused'))]
        db.add_all(extra); db.commit()
        extra_ids=[x.id for x in extra]
        db.add_all([LessonDay(lesson_id=x,day_number=1,title='Local assigned session',
                             activity_type='Weekly Lesson',status='published') for x in extra_ids])
        db.commit()
    if populated:
        with engine.begin() as c:
            c.execute(sa.text('UPDATE lessons SET curriculum_week=10 WHERE id=:id'), {'id':extra_ids[0]})
            c.execute(sa.text('UPDATE lessons SET curriculum_week=11 WHERE id=:id'), {'id':extra_ids[1]})
            for cancelled in (False, True):
                c.execute(sa.text('INSERT INTO lesson_assignments (child_id,lesson_id,day_number,assigned_by,scheduled_date,priority,cancelled) VALUES (:child,:lesson,1,:parent,:date,:priority,:cancelled)'),
                          dict(child=families[0]['child_id'],lesson=extra_ids[0],parent=families[0]['parent_id'],
                               date='2026-11-25',priority=int(cancelled),cancelled=cancelled))
    with engine.connect() as c:
        assert schema_is_compatible(c)
    before=history_snapshot(engine,populated)
    def dependency():
        with factory() as db:yield db
    old_overrides=main.app.dependency_overrides.copy()
    main.app.dependency_overrides[get_db]=dependency
    try:
        with patch.object(main.settings,'ENVIRONMENT','production'),patch.object(main,'SessionLocal',factory),TestClient(main.app) as client:
            assert client.get('/health').status_code==200
            assert client.get('/ready').status_code==200
            auth=[]
            for family in families:
                row={}
                for role in ('parent','student'):
                    response=client.post('/api/auth/login',json={'email':f"{family['programme']}-{role}@example.test",'password':password})
                    assert response.status_code==200,response.text
                    assert response.json()['user']['programme']==family['programme']
                    row[role]={'Authorization':'Bearer '+response.json()['access_token']}
                auth.append(row)
                assert client.get(f"/api/parent/dashboard/{family['parent_id']}",headers=row['parent']).status_code==200
                assert client.get(f"/api/student/dashboard/{family['child_id']}",headers=row['student']).status_code==200
                assert client.get(f"/api/curriculum/lessons/{family['lesson_id']}",headers=row['student']).status_code==200
                assert client.get(f"/api/lessons/session/{family['child_id']}/{family['lesson_id']}/1",headers=row['student']).status_code==200
                # Ordinary profile updates must not rewrite unknown week/assignment fields.
                assert client.patch(f"/api/parent/children/{family['child_id']}",headers=row['parent'],json={'name':'Updated Local Child'}).status_code==200
            assert client.get(f"/api/curriculum/lessons/{families[0]['lesson_id']}",headers=auth[1]['student']).status_code==403
            assert client.get(f"/api/student/dashboard/{families[0]['child_id']}",headers=auth[1]['parent']).status_code==403
            assert client.get(f"/api/parent/dashboard/{families[0]['parent_id']}",headers=auth[0]['student']).status_code==403
            assert client.get('/api/admin/dashboard',headers=auth[0]['parent']).status_code==403
            assert client.post('/api/auth/login',json={'email':'homeschool-parent@example.test','password':'WrongPassword'}).status_code==401
            admin_login=client.post('/api/auth/login',json={'email':'local-admin@example.test','password':password})
            admin_headers={'Authorization':'Bearer '+admin_login.json()['access_token']}
            assert client.get(f"/api/curriculum/lessons/{families[0]['lesson_id']}",headers=admin_headers).status_code==200
            if populated:
                for lesson_id in extra_ids[:2]:
                    dep=client.get(f'/api/curriculum/admin/lessons/{lesson_id}/dependencies',headers=admin_headers)
                    assert dep.status_code==200 and dep.json()['can_delete'] is False
                    assert client.delete(f'/api/curriculum/admin/lessons/{lesson_id}',headers=admin_headers).status_code==409
                assert dep.json()['dependencies']['authored_curriculum_week']==1
            assert client.delete(f'/api/curriculum/admin/lessons/{extra_ids[2]}',headers=admin_headers).status_code==200
            # Missing new feature routes are deliberate: recovery uses the previous frontend.
            assert client.get(f"/api/student/lesson-options/{families[0]['child_id']}",headers=auth[0]['student']).status_code==404
    finally:
        main.app.dependency_overrides.clear();main.app.dependency_overrides.update(old_overrides)
    if populated:
        import csv
        import io
        from backend.services.curriculum_importer import import_curriculum_csv_data
        row={'Subject':'Mathematics','Level':'Level 0','Unit_Name':'Number Sense','Subtopic':'Assigned counting',
             'Lesson Number':'2','Lesson Title':'Assigned only','Lesson Type':'Weekly Lesson',
             'Learning objectives':'Synthetic objective','Key_concept':'Synthetic concept',
             'AI_Teaching_Script':'Synthetic fixture only','Status':'Published'}
        output=io.StringIO();writer=csv.DictWriter(output,fieldnames=list(row));writer.writeheader();writer.writerow(row)
        with factory() as db:
            result=import_curriculum_csv_data(output.getvalue(),db)
            assert result['matched_lessons']==1 and result['lessons_created']==0
            db.commit()
    assert history_snapshot(engine,populated)==before
    return {'revision':revision,'populated':populated,'auth_and_programme_isolation':'PASS','history_and_new_data_preserved':'PASS'}


@pytest.mark.parametrize('revision,populated',[('0013',False),('0014',False),('0014',True)])
def test_recovery_contract(revision,populated):
    engine=sa.create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    sa.event.listen(engine,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'))
    try:exercise_recovery(engine,revision,populated)
    finally:engine.dispose()


@pytest.mark.parametrize('revision',['0012_curriculum_safety','0015_unknown','0014_partial'])
def test_unknown_or_partial_revision_fails_closed(revision):
    engine=sa.create_engine('sqlite://')
    make_0013(engine)
    with engine.begin() as c:c.execute(sa.text('UPDATE alembic_version SET version_num=:v'),{'v':revision})
    with engine.connect() as c:assert not schema_is_compatible(c)
    with patch.object(main.settings,'ENVIRONMENT','production'),patch.object(main,'SessionLocal',sessionmaker(bind=engine)):
        assert main.readiness_check().status_code==503
    engine.dispose()


def test_missing_mapped_column_and_multiple_heads_fail_closed():
    engine=sa.create_engine('sqlite://')
    make_0013(engine)
    with engine.begin() as c:
        c.execute(sa.text("INSERT INTO alembic_version VALUES ('0014_lesson_assignments')"))
    with engine.connect() as c:assert not schema_is_compatible(c)
    with engine.begin() as c:
        c.execute(sa.text("DELETE FROM alembic_version WHERE version_num='0014_lesson_assignments'"))
        c.execute(sa.text('ALTER TABLE lessons RENAME COLUMN learn_content TO missing_content'))
    with engine.connect() as c:assert not schema_is_compatible(c)
    engine.dispose()


@pytest.mark.parametrize('damage',["UPDATE alembic_version SET version_num='0014_lesson_assignments'",
    'DROP INDEX uq_child_assignment_date','DROP TABLE lesson_assignments'])
def test_0014_incomplete_shape_fails_closed(damage):
    engine=sa.create_engine('sqlite://')
    make_0013(engine)
    if not damage.startswith('UPDATE'):apply_0014(engine)
    with engine.begin() as c:c.execute(sa.text(damage))
    with engine.connect() as c:assert not schema_is_compatible(c)
    engine.dispose()
