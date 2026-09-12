import importlib
import sys
import types

import sqlalchemy as sa

if "alembic" not in sys.modules:
    sys.modules["alembic"] = types.SimpleNamespace(op=types.SimpleNamespace())

MIGRATION = importlib.import_module("backend.migrations.versions.0012_curriculum_safety")


class Recorder:
    def __init__(self):
        self.columns = []
        self.dropped = []
        self.foreign_keys = []

    def add_column(self, table, column):
        self.columns.append((table, column))

    def drop_constraint(self, name, table, type_=None):
        self.dropped.append((name, table, type_))

    def create_foreign_key(self, *args, **kwargs):
        self.foreign_keys.append((args, kwargs))


def test_upgrade_adds_safety_flags_and_restricts_attempt_deletion(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(MIGRATION, "op", recorder)
    MIGRATION.upgrade()
    columns = {column.name: column for table, column in recorder.columns if table == "lessons"}
    assert set(columns) == {"archived", "quiz_review_required"}
    assert all(column.nullable is False for column in columns.values())
    assert ("quiz_attempts_lesson_id_fkey", "quiz_attempts", "foreignkey") in recorder.dropped
    args, kwargs = recorder.foreign_keys[-1]
    assert args[:3] == ("quiz_attempts_lesson_id_fkey", "quiz_attempts", "lessons")
    assert kwargs["ondelete"] == "RESTRICT"
