import csv
import io
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    AIInteraction, Child, LearningEvidence, Lesson, LessonDay, LessonSession,
    QuizAttempt, QuizQuestion, StudentProgress, Subject, Unit, User,
)
from backend.routers.curriculum import (
    ArchiveLessonRequest, delete_lesson, get_lesson_detail, set_lesson_archive,
)
from backend.services.curriculum_importer import import_curriculum_csv_data


HEADERS = [
    "Curriculum Country", "Subject", "Level", "Unit_Name", "Subtopic", "Lesson Number",
    "Lesson Title", "Lesson Type", "Learning objectives", "Key_concept", "AI_Teaching_Script",
    "Practice Question", "Status",
]


def curriculum_csv(*, unit="Number Sense", script="Teach counting", status="Published"):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=HEADERS)
    writer.writeheader()
    for day, activity in ((1, "Explore"), (2, "Practice"), (3, "Apply")):
        writer.writerow({
            "Curriculum Country": "UK", "Subject": "Mathematics", "Level": "Level 0",
            "Unit_Name": unit, "Subtopic": "Counting to 5", "Lesson Number": "1",
            "Lesson Title": "Counting", "Lesson Type": f"Day {day} - {activity}",
            "Learning objectives": "Count five objects", "Key_concept": "One number per object",
            "AI_Teaching_Script": f"{script} day {day}", "Practice Question": "Count five stars",
            "Status": status,
        })
    return output.getvalue()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def users_and_child(db):
    admin = User(email=f"admin-{uuid.uuid4()}@test.local", name="Admin", password_hash="x", role="admin")
    parent = User(email=f"parent-{uuid.uuid4()}@test.local", name="Parent", password_hash="x", role="parent")
    db.add_all([admin, parent]); db.flush()
    child = Child(parent_id=parent.id, name="Learner", level=0)
    db.add(child); db.flush()
    return admin, parent, child


def make_lesson(db):
    subject = Subject(title=f"Math {uuid.uuid4()}", slug=f"math-{uuid.uuid4()}")
    db.add(subject); db.flush()
    unit = Unit(subject_id=subject.id, level=0, title="Number Sense", order_num=1)
    db.add(unit); db.flush()
    lesson = Lesson(unit_id=unit.id, level=0, title="Lesson 1", topic="Counting", order_num=1, learn_content="Count")
    db.add(lesson); db.flush()
    for number, activity in ((1, "Explore"), (2, "Practice"), (3, "Apply")):
        db.add(LessonDay(lesson_id=lesson.id, day_number=number, activity_type=activity, title=activity, status="published"))
    db.flush()
    return lesson


def test_reimport_preserves_ids_publication_quizzes_attempts_and_flags_review(db):
    first = import_curriculum_csv_data(curriculum_csv(), db)
    db.commit()
    lesson = db.query(Lesson).one()
    lesson_id = lesson.id
    day_ids = [day.id for day in lesson.days]
    assert first["lessons_created"] == 1
    assert {day.status for day in lesson.days} == {"pending"}
    for day in lesson.days:
        day.status = "published"
    _, _, child = users_and_child(db)
    question = QuizQuestion(lesson_id=lesson.id, question="How many?", options=["5"], correct_answer="5")
    attempt = QuizAttempt(submission_id=str(uuid.uuid4()), child_id=child.id, lesson_id=lesson.id, day_number=1,
                          score_percentage=100, correct_count=1, total_questions=1,
                          submitted_answers=[{"selected_answer": "5"}], passed=True, xp_earned=0)
    db.add_all([question, attempt]); db.commit()

    stats = import_curriculum_csv_data(curriculum_csv(script="Teach counting clearly", status="Pending"), db)
    db.commit(); db.expire_all()
    updated = db.query(Lesson).filter_by(id=lesson_id).one()
    assert [day.id for day in updated.days] == day_ids
    assert {day.status for day in updated.days} == {"published"}
    assert "clearly" in updated.days[0].ai_script
    assert updated.quiz_review_required is True
    assert stats["quiz_reviews_flagged"] == 1
    assert db.query(QuizQuestion).filter_by(lesson_id=lesson_id).count() == 1
    assert db.query(QuizAttempt).filter_by(lesson_id=lesson_id).count() == 1


def test_hierarchy_change_is_reported_and_does_not_replace_existing_lesson(db):
    import_curriculum_csv_data(curriculum_csv(), db); db.commit()
    original_id = db.query(Lesson).one().id
    stats = import_curriculum_csv_data(curriculum_csv(unit="Renamed Number Sense"), db)
    assert db.query(Lesson).count() == 2
    assert db.query(Lesson).filter_by(id=original_id).one()
    kinds = {item["type"] for item in stats["hierarchy_identity_changes"]}
    assert {"new_unit", "new_lesson"}.issubset(kinds)


def test_unused_lesson_delete_removes_only_curriculum_owned_rows(db):
    admin, _, _ = users_and_child(db)
    lesson = make_lesson(db)
    db.add(QuizQuestion(lesson_id=lesson.id, question="Q", options=["A"], correct_answer="A")); db.commit()
    lesson_id = lesson.id
    result = delete_lesson(lesson_id, db, admin)
    assert result["deleted"] is True
    assert db.query(Lesson).filter_by(id=lesson_id).count() == 0
    assert db.query(LessonDay).filter_by(lesson_id=lesson_id).count() == 0
    assert db.query(QuizQuestion).filter_by(lesson_id=lesson_id).count() == 0


@pytest.mark.parametrize("dependency", ["progress", "evidence", "session", "interaction", "attempt"])
def test_history_dependency_blocks_delete_atomically(db, dependency):
    admin, _, child = users_and_child(db)
    lesson = make_lesson(db)
    records = {
        "progress": StudentProgress(child_id=child.id, lesson_id=lesson.id, day_number=1),
        "evidence": LearningEvidence(child_id=child.id, lesson_id=lesson.id, subject="Math", lesson_title="Counting",
                                     skill="Counting", content="work", ai_feedback="Good"),
        "session": LessonSession(child_id=child.id, lesson_id=lesson.id, day_number=1),
        "interaction": AIInteraction(child_id=child.id, lesson_id=lesson.id, day_number=1),
        "attempt": QuizAttempt(submission_id=str(uuid.uuid4()), child_id=child.id, lesson_id=lesson.id, day_number=1,
                               score_percentage=100, correct_count=1, total_questions=1,
                               submitted_answers=[], passed=True, xp_earned=0),
    }
    db.add(records[dependency]); db.commit()
    day_count = db.query(LessonDay).filter_by(lesson_id=lesson.id).count()
    with pytest.raises(HTTPException) as error:
        delete_lesson(lesson.id, db, admin)
    assert error.value.status_code == 409
    assert error.value.detail["dependencies"][{
        "progress": "student_progress", "evidence": "learning_evidence", "session": "lesson_sessions",
        "interaction": "ai_interactions", "attempt": "quiz_attempts",
    }[dependency]] == 1
    assert db.query(Lesson).filter_by(id=lesson.id).count() == 1
    assert db.query(LessonDay).filter_by(lesson_id=lesson.id).count() == day_count


def test_archive_preserves_history_and_blocks_new_non_admin_access(db):
    admin, parent, child = users_and_child(db)
    lesson = make_lesson(db)
    attempt = QuizAttempt(submission_id=str(uuid.uuid4()), child_id=child.id, lesson_id=lesson.id, day_number=1,
                          score_percentage=100, correct_count=1, total_questions=1,
                          submitted_answers=[], passed=True, xp_earned=0)
    db.add(attempt); db.commit()
    result = set_lesson_archive(lesson.id, ArchiveLessonRequest(archived=True), db, admin)
    assert result["archived"] is True
    assert db.query(LessonDay).filter_by(lesson_id=lesson.id).count() == 3
    assert db.query(QuizAttempt).filter_by(lesson_id=lesson.id).count() == 1
    with pytest.raises(HTTPException) as error:
        get_lesson_detail(lesson.id, db, parent)
    assert error.value.status_code == 404
    assert get_lesson_detail(lesson.id, db, admin).archived is True


def test_importer_is_transactionally_recoverable_on_invalid_later_row(db):
    rows = curriculum_csv().splitlines()
    broken = "\n".join(rows + [rows[1].replace("Day 1 - Explore", "Day 4 - Explore")])
    with pytest.raises(ValueError):
        import_curriculum_csv_data(broken, db)
    db.rollback()
    assert db.query(Lesson).count() == 0
