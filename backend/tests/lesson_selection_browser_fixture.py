"""Synthetic local browser fixtures; never use against an existing database."""
import os
from pathlib import Path


def main():
    url = os.environ.get('DATABASE_URL', '')
    assert url.startswith('sqlite:///'), 'Disposable SQLite required'
    path = Path(url.removeprefix('sqlite:///')).resolve()
    assert path.name.startswith('hwe-selection-browser-') and not path.exists(), 'New uniquely named fixture database required'
    from backend.database import Base, engine, SessionLocal
    from backend.models import User, Child, Subject, ChildSubject, Unit, Lesson, LessonDay, StudentProgress
    from backend.routers.auth import get_password_hash
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        parent = User(email='planning-parent@example.test', name='Planning QA', role='parent', programme='homeschool', password_hash=get_password_hash('LocalPlanning123!'))
        student = User(email='planning-student@example.test', name='Planning student', role='student', programme='homeschool', password_hash=get_password_hash('LocalPlanning123!'))
        db.add_all([parent, student]); db.flush()
        child = Child(parent_id=parent.id, user_id=student.id, name='Planning child', level=0)
        db.add(child); db.flush()
        for title, slug, week in [('Mathematics', 'mathematics', 10), ('English Language', 'english-language', None)]:
            subject = Subject(title=title, slug=slug); db.add(subject); db.flush()
            db.add(ChildSubject(child_id=child.id, subject_id=subject.id))
            unit = Unit(subject_id=subject.id, title='Synthetic QA unit', level=0); db.add(unit); db.flush()
            lesson = Lesson(unit_id=unit.id, title=f'{title} QA fixture', level=0, order_num=1, curriculum_week=week, learn_content='Synthetic local layout fixture only.')
            db.add(lesson); db.flush()
            db.add(LessonDay(lesson_id=lesson.id, day_number=1, activity_type='Weekly Lesson', title='Synthetic QA session', status='published'))
        db.commit()
        assert db.query(StudentProgress).count() == 0
    print('Disposable local browser fixture created; Week 10 is synthetic test metadata.')


if __name__ == '__main__': main()
