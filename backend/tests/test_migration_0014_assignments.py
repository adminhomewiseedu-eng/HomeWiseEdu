"""Run real Alembic operations in a subprocess, isolated from legacy op mocks."""
import subprocess
import sys
from pathlib import Path


def test_real_0014_upgrade_downgrade_preservation():
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--verify'], check=True, timeout=30)


def verify():
    import importlib
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    migration = importlib.import_module('backend.migrations.versions.0014_lesson_assignments')
    engine = sa.create_engine('sqlite://')
    with engine.begin() as conn:
        conn.exec_driver_sql('PRAGMA foreign_keys=ON')
        conn.exec_driver_sql('CREATE TABLE users (id INTEGER PRIMARY KEY, programme TEXT NOT NULL)')
        conn.exec_driver_sql('CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES users(id))')
        conn.exec_driver_sql('CREATE TABLE lessons (id INTEGER PRIMARY KEY, title TEXT)')
        conn.exec_driver_sql('CREATE TABLE student_progress (id INTEGER PRIMARY KEY, lesson_id INTEGER, quiz_score INTEGER)')
        conn.exec_driver_sql("INSERT INTO users VALUES (1, 'homeschool'), (2, 'bible_study')")
        conn.exec_driver_sql('INSERT INTO children VALUES (1, 1)')
        conn.exec_driver_sql("INSERT INTO lessons VALUES (1, 'Existing lesson')")
        conn.exec_driver_sql('INSERT INTO student_progress VALUES (1, 1, 80)')
        op = Operations(MigrationContext.configure(conn))
        migration.op = op
        migration.upgrade()
        assert conn.exec_driver_sql('SELECT curriculum_week FROM lessons').scalar() is None
        assert conn.exec_driver_sql('SELECT quiz_score FROM student_progress').scalar() == 80
        for sql in ['UPDATE lessons SET curriculum_week=0', 'UPDATE lessons SET curriculum_week=-1']:
            try: conn.exec_driver_sql(sql)
            except sa.exc.IntegrityError: pass
            else: raise AssertionError('Invalid week accepted')
        conn.exec_driver_sql('UPDATE lessons SET curriculum_week=10')
        try: migration.downgrade()
        except RuntimeError: pass
        else: raise AssertionError('Downgrade destroyed authored week')
        conn.exec_driver_sql('UPDATE lessons SET curriculum_week=NULL')
        conn.exec_driver_sql("INSERT INTO lesson_assignments (child_id,lesson_id,day_number,assigned_by,scheduled_date) VALUES (1,1,1,1,'2026-11-10')")
        try: migration.downgrade()
        except RuntimeError: pass
        else: raise AssertionError('Downgrade destroyed assignment')
        try:
            conn.exec_driver_sql("INSERT INTO lesson_assignments (child_id,lesson_id,day_number,assigned_by,scheduled_date) VALUES (1,1,1,1,'2026-11-10')")
        except sa.exc.IntegrityError: pass
        else: raise AssertionError('Duplicate assignment accepted')
        try: conn.exec_driver_sql('DELETE FROM lessons WHERE id=1')
        except sa.exc.IntegrityError: pass
        else: raise AssertionError('Assignment FK did not protect lesson')
        conn.exec_driver_sql('DELETE FROM lesson_assignments')
        migration.downgrade()
        assert 'curriculum_week' not in {x['name'] for x in sa.inspect(conn).get_columns('lessons')}
        migration.upgrade()
        assert conn.exec_driver_sql('SELECT quiz_score FROM student_progress').scalar() == 80
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM users').scalar() == 2
        assert conn.exec_driver_sql("SELECT programme FROM users WHERE id=2").scalar() == 'bible_study'
    print('Real disposable SQLite 0013 -> 0014 -> 0013 -> 0014: PASS')


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    verify()
