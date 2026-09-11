import importlib
import sys
import types

import pytest
import sqlalchemy as sa


if "alembic" not in sys.modules:
    sys.modules["alembic"] = types.SimpleNamespace(op=types.SimpleNamespace())

MIGRATION = importlib.import_module(
    "backend.migrations.versions.0010_provision_lesson_37_quiz"
)


def _database(level=0, subject="Mathematics", unit="Number Sense", topic="Counting to 5"):
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    subjects = sa.Table(
        "subjects", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
    )
    units = sa.Table(
        "units", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("subject_id", sa.Integer, nullable=False),
        sa.Column("title", sa.String, nullable=False),
    )
    lessons = sa.Table(
        "lessons", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("unit_id", sa.Integer, nullable=False),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("topic", sa.String, nullable=False),
    )
    quiz_questions = sa.Table(
        "quiz_questions", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lesson_id", sa.Integer, nullable=False),
        sa.Column("question", sa.String, nullable=False),
        sa.Column("options", sa.JSON, nullable=False),
        sa.Column("correct_answer", sa.String, nullable=False),
        sa.Column("explanation_correct", sa.String),
        sa.Column("explanation_incorrect", sa.String),
    )
    metadata.create_all(engine)
    connection = engine.connect()
    connection.execute(subjects.insert(), {"id": 1, "title": subject})
    connection.execute(units.insert(), {"id": 1, "subject_id": 1, "title": unit})
    connection.execute(lessons.insert(), {
        "id": 37, "unit_id": 1, "level": level, "topic": topic,
    })
    return connection, quiz_questions


def test_upgrade_inserts_only_missing_canonical_questions(monkeypatch):
    connection, questions = _database()
    connection.execute(questions.insert(), {
        "lesson_id": 37,
        **MIGRATION.REVIEWED_QUESTIONS[0],
    })
    monkeypatch.setattr(MIGRATION.op, "get_bind", lambda: connection, raising=False)

    MIGRATION.upgrade()
    MIGRATION.upgrade()

    rows = connection.execute(
        sa.select(questions).where(questions.c.lesson_id == 37)
    ).mappings().all()
    assert len(rows) == 3
    assert [row["question"] for row in rows] == [
        item["question"] for item in MIGRATION.REVIEWED_QUESTIONS
    ]
    for row, expected in zip(rows, MIGRATION.REVIEWED_QUESTIONS):
        assert row["options"] == expected["options"]
        assert row["correct_answer"] == expected["correct_answer"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("level", 1),
        ("subject", "English"),
        ("unit", "Early Addition"),
        ("topic", "Counting to 10"),
    ],
)
def test_upgrade_refuses_mismatched_lesson_identity(monkeypatch, field, value):
    kwargs = {field: value}
    connection, questions = _database(**kwargs)
    monkeypatch.setattr(MIGRATION.op, "get_bind", lambda: connection, raising=False)

    with pytest.raises(RuntimeError, match="identity does not match"):
        MIGRATION.upgrade()

    assert connection.execute(sa.select(sa.func.count()).select_from(questions)).scalar_one() == 0
