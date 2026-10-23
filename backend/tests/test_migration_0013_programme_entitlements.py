import contextlib
import importlib
import sys
import types

import pytest

if "alembic" not in sys.modules:
    sys.modules["alembic"] = types.SimpleNamespace(op=types.SimpleNamespace())

MIGRATION = importlib.import_module("backend.migrations.versions.0013_programme_entitlements")


class BatchRecorder:
    def __init__(self, owner):
        self.owner = owner

    def create_check_constraint(self, name, condition):
        self.owner.checks.append((name, condition))

    def drop_constraint(self, name, type_=None):
        self.owner.dropped.append((name, type_))


class Recorder:
    def __init__(self, bible_accounts=0):
        self.columns = []
        self.sql = []
        self.checks = []
        self.dropped = []
        self.bible_accounts = bible_accounts

    def add_column(self, table, column):
        self.columns.append((table, column))

    def execute(self, statement):
        self.sql.append(statement)

    @contextlib.contextmanager
    def batch_alter_table(self, table):
        assert table == "users"
        yield BatchRecorder(self)

    def drop_column(self, table, column):
        self.dropped.append((table, column))

    def get_bind(self):
        return BindRecorder(self.bible_accounts)


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class BindRecorder:
    def __init__(self, bible_accounts):
        self.bible_accounts = bible_accounts

    def execute(self, statement):
        assert "programme = 'bible_study'" in str(statement)
        return ScalarResult(self.bible_accounts)


def test_upgrade_defaults_and_backfills_existing_users(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(MIGRATION, "op", recorder)

    MIGRATION.upgrade()

    table, column = recorder.columns[0]
    assert table == "users"
    assert column.name == "programme"
    assert column.nullable is False
    assert str(column.server_default.arg) == "homeschool"
    assert recorder.sql == ["UPDATE users SET programme = 'homeschool' WHERE programme IS NULL"]
    assert recorder.checks == [
        ("ck_users_programme", "programme IN ('homeschool', 'bible_study')")
    ]


def test_downgrade_refuses_to_destroy_bible_programme_classification(monkeypatch):
    recorder = Recorder(bible_accounts=1)
    monkeypatch.setattr(MIGRATION, "op", recorder)

    with pytest.raises(RuntimeError, match="Bible Study accounts exist"):
        MIGRATION.downgrade()

    assert recorder.dropped == []


def test_downgrade_remains_available_before_any_bible_accounts_exist(monkeypatch):
    recorder = Recorder(bible_accounts=0)
    monkeypatch.setattr(MIGRATION, "op", recorder)

    MIGRATION.downgrade()

    assert recorder.dropped == [
        ("ck_users_programme", "check"),
        ("users", "programme"),
    ]
