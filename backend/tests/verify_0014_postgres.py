"""Standalone real PostgreSQL migration check; creates only a disposable local cluster."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    tools = Path(r'C:\Program Files\PostgreSQL\18\bin')
    assert (tools / 'initdb.exe').is_file(), 'Existing PostgreSQL 18 tools required'
    workspace = Path(tempfile.mkdtemp(prefix='hwe-0014-pg-')).resolve()
    assert workspace.parent == Path(tempfile.gettempdir()).resolve()
    data = workspace / 'data'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PG', 'RAILWAY_'))}
    env.update(DATABASE_URL=f'postgresql+psycopg://hwe_assignment_qa@127.0.0.1:{port}/postgres',
               ENVIRONMENT='test', AUTO_INIT_DB='false', SEED_MODE='none')
    def native(exe, args, timeout=60, check=True):
        with (workspace / f'{exe}.log').open('ab') as log:
            return subprocess.run([str(tools / f'{exe}.exe'), *args], env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=timeout, check=check)
    started = False
    try:
        native('initdb', ['-D', str(data), '-U', 'hwe_assignment_qa', '--auth=trust', '--encoding=UTF8'])
        started = True  # also attempt shutdown if startup fails after spawning postgres
        native('pg_ctl', ['-D', str(data), '-l', str(workspace / 'postgres.log'), '-o', f'-h 127.0.0.1 -p {port}', '-w', '-t', '30', 'start'], timeout=45)
        os.environ.update(env)
        for key in list(os.environ):
            if key.startswith('RAILWAY_'): del os.environ[key]
        verify_schema(root)
        print('PostgreSQL 18 real Alembic 0013 -> 0014 -> 0013 -> 0014: PASS')
        print('Constraints, downgrade refusal, programme and historical record preservation: PASS')
    finally:
        if started:
            result = native('pg_ctl', ['-D', str(data), '-m', 'fast', '-w', '-t', '20', 'stop'], timeout=30, check=False)
            if result.returncode != 0:
                native('pg_ctl', ['-D', str(data), '-m', 'immediate', '-w', '-t', '10', 'stop'], timeout=20, check=False)
            status = native('pg_ctl', ['-D', str(data), 'status'], timeout=10, check=False)
            if status.returncode != 3:
                raise RuntimeError(f'Disposable PostgreSQL shutdown not confirmed; inspect {workspace}')
            print('Disposable PostgreSQL stopped; synthetic test logs retained at', workspace)


def verify_schema(root):
    import uuid
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from backend.database import Base, engine, SessionLocal
    from backend.models import User, Child, Subject, Unit, Lesson, LessonDay, QuizQuestion, QuizAttempt, StudentProgress, LessonSession, LearningEvidence, ChildSubject
    # Build a faithful pre-0014 schema from current metadata, then remove only the new objects.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        parent = User(email='local-parent@example.test', name='Parent', password_hash='synthetic', role='parent', programme='homeschool')
        bible = User(email='local-bible@example.test', name='Bible', password_hash='synthetic', role='parent', programme='bible_study')
        student = User(email='local-student@example.test', name='Student', password_hash='synthetic', role='student', programme='homeschool')
        admin = User(email='local-admin@example.test', name='Admin', password_hash='synthetic', role='admin', programme='homeschool')
        db.add_all([parent, bible, student, admin]); db.flush()
        child = Child(parent_id=parent.id, user_id=student.id, name='Child', level=0)
        subject = Subject(title='QA Subject', slug='qa'); db.add_all([child, subject]); db.flush()
        unit = Unit(subject_id=subject.id, title='QA Unit', level=0); db.add(unit); db.flush()
        lesson = Lesson(unit_id=unit.id, title='QA Lesson', learn_content='Synthetic fixture', level=0); db.add(lesson); db.flush()
        db.add_all([ChildSubject(child_id=child.id, subject_id=subject.id),
            LessonDay(lesson_id=lesson.id, day_number=1, title='QA', status='published'),
            QuizQuestion(lesson_id=lesson.id, question='QA', options=['QA'], correct_answer='QA'),
            QuizAttempt(submission_id=str(uuid.uuid4()), child_id=child.id, lesson_id=lesson.id, day_number=1,
                score_percentage=100, correct_count=1, total_questions=1, submitted_answers=[{'selected_answer': 'QA'}], passed=True, xp_earned=0),
            StudentProgress(child_id=child.id, lesson_id=lesson.id, day_number=1, status='completed', quiz_score=80),
            LessonSession(child_id=child.id, lesson_id=lesson.id, day_number=1, pedagogical_state={'current_phase': 'PRACTICE_READY'}),
            LearningEvidence(child_id=child.id, lesson_id=lesson.id, subject='QA', lesson_title='QA', skill='QA', ai_feedback='Synthetic feedback')])
        db.commit()
    tables = ['users', 'children', 'child_subjects', 'lesson_days', 'quiz_questions', 'quiz_attempts', 'student_progress', 'lesson_sessions', 'learning_evidence']
    def snapshot():
        with engine.connect() as conn:
            return {table: conn.execute(sa.text(f'SELECT COUNT(*) FROM {table}')).scalar_one() for table in tables}
    expected = snapshot()
    with engine.begin() as conn:
        conn.exec_driver_sql('DROP TABLE lesson_assignments')
        conn.exec_driver_sql('ALTER TABLE lessons DROP CONSTRAINT ck_lesson_curriculum_week')
        conn.exec_driver_sql('ALTER TABLE lessons DROP COLUMN curriculum_week')
        conn.exec_driver_sql('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)')
        conn.exec_driver_sql("INSERT INTO alembic_version VALUES ('0013_programme_entitlements')")
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'backend/migrations'))
    command.upgrade(config, '0014_lesson_assignments')
    assert snapshot() == expected
    with engine.begin() as conn:
        assert conn.exec_driver_sql('SELECT curriculum_week FROM lessons').scalar_one() is None
        for invalid in (0, -1):
            try:
                with conn.begin_nested(): conn.execute(sa.text('UPDATE lessons SET curriculum_week=:w'), {'w': invalid})
            except sa.exc.IntegrityError: pass
            else: raise AssertionError('Invalid curriculum week accepted')
        conn.exec_driver_sql('UPDATE lessons SET curriculum_week=10')
        conn.exec_driver_sql("INSERT INTO lesson_assignments(child_id,lesson_id,day_number,assigned_by,scheduled_date) SELECT c.id,l.id,1,c.parent_id,'2026-11-10' FROM children c CROSS JOIN lessons l")
        for invalid_sql in [
            "INSERT INTO lesson_assignments(child_id,lesson_id,day_number,assigned_by,scheduled_date) SELECT c.id,l.id,1,c.parent_id,'2026-11-10' FROM children c CROSS JOIN lessons l",
            'UPDATE lesson_assignments SET priority=-1', 'DELETE FROM lessons',
        ]:
            try:
                with conn.begin_nested(): conn.exec_driver_sql(invalid_sql)
            except sa.exc.IntegrityError: pass
            else: raise AssertionError('Assignment constraint failed')
    try: command.downgrade(config, '0013_programme_entitlements')
    except RuntimeError: pass
    else: raise AssertionError('Unsafe downgrade was accepted')
    with engine.begin() as conn:
        assert conn.exec_driver_sql('SELECT curriculum_week FROM lessons').scalar_one() == 10
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM lesson_assignments').scalar_one() == 1
        conn.exec_driver_sql('DELETE FROM lesson_assignments')
        conn.exec_driver_sql('UPDATE lessons SET curriculum_week=NULL')
    command.downgrade(config, '0013_programme_entitlements')
    command.upgrade(config, '0014_lesson_assignments')
    assert snapshot() == expected
    with engine.connect() as conn:
        assert conn.exec_driver_sql('SELECT version_num FROM alembic_version').scalar_one() == '0014_lesson_assignments'
        assert conn.exec_driver_sql("SELECT COUNT(*) FROM users WHERE programme='bible_study'").scalar_one() == 1
        assert conn.exec_driver_sql('SELECT quiz_score FROM student_progress').scalar_one() == 80
    engine.dispose()


if __name__ == '__main__': main()
