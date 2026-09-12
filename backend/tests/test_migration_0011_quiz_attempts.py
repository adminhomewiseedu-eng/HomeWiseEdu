import importlib
import sys
import types

import sqlalchemy as sa


if "alembic" not in sys.modules:
    sys.modules["alembic"] = types.SimpleNamespace(op=types.SimpleNamespace())

MIGRATION = importlib.import_module("backend.migrations.versions.0011_quiz_attempts")


class OperationRecorder:
    def __init__(self):
        self.table = None
        self.indexes = []

    def create_table(self, name, *elements):
        self.table = (name, elements)

    def create_index(self, name, table_name, columns, unique=False):
        self.indexes.append((name, table_name, columns, unique))


def test_upgrade_declares_attempt_table_constraints_indexes_and_foreign_keys(monkeypatch):
    recorder = OperationRecorder()
    monkeypatch.setattr(MIGRATION, "op", recorder)
    MIGRATION.upgrade()

    table_name, elements = recorder.table
    assert table_name == "quiz_attempts"
    columns = {element.name: element for element in elements if isinstance(element, sa.Column)}
    assert columns["submission_id"].nullable is False
    assert columns["submitted_answers"].nullable is False
    assert columns["correct_count"].nullable is False
    foreign_keys = [element for element in elements if isinstance(element, sa.ForeignKeyConstraint)]
    assert {next(iter(fk.elements)).target_fullname for fk in foreign_keys} == {"children.id", "lessons.id"}
    assert all(fk.ondelete == "CASCADE" for fk in foreign_keys)
    checks = {element.name for element in elements if isinstance(element, sa.CheckConstraint)}
    assert checks == {
        "ck_quiz_attempt_score_percentage", "ck_quiz_attempt_correct_count",
        "ck_quiz_attempt_total_questions", "ck_quiz_attempt_counts",
    }
    assert ("ix_quiz_attempts_submission_id", "quiz_attempts", ["submission_id"], True) in recorder.indexes
    assert (
        "ix_quiz_attempts_child_lesson_day_completed", "quiz_attempts",
        ["child_id", "lesson_id", "day_number", "completed_at"], False,
    ) in recorder.indexes
