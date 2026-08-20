"""Upgrade a legacy database with Phase 1, Phase 2 and Phase 3 integrity fields.

Existing databases: verify duplicate session/progress keys, stamp 0001, then run this
revision. Clean databases already contain these objects and the checks are no-ops.

Revision ID: 0002_phase_hardening
Revises: 0001_current_schema
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002_phase_hardening"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None


def _columns(inspector, table):
    return {column["name"] for column in inspector.get_columns(table)}


def _unique_names(inspector, table):
    return {item.get("name") for item in inspector.get_unique_constraints(table)} | {item.get("name") for item in inspector.get_indexes(table) if item.get("unique")}


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "pedagogical_state" not in _columns(inspector, "lesson_sessions"):
        op.add_column("lesson_sessions", sa.Column("pedagogical_state", sa.JSON(), nullable=True))
    if "quiz_xp_awarded" not in _columns(inspector, "student_progress"):
        op.add_column("student_progress", sa.Column("quiz_xp_awarded", sa.Boolean(), server_default=sa.false(), nullable=False))
    if "completion_xp_awarded" not in _columns(inspector, "learning_evidence"):
        op.add_column("learning_evidence", sa.Column("completion_xp_awarded", sa.Boolean(), server_default=sa.false(), nullable=False))
    if "stored_file_name" not in _columns(inspector, "learning_evidence"):
        op.add_column("learning_evidence", sa.Column("stored_file_name", sa.String(), nullable=True))

    for table, name in (("lesson_sessions", "uq_lesson_session_child_lesson_day"), ("student_progress", "uq_student_progress_child_lesson_day")):
        if name not in _unique_names(inspector, table):
            duplicate = bind.execute(sa.text(
                f"SELECT 1 FROM {table} GROUP BY child_id, lesson_id, day_number HAVING COUNT(*) > 1 LIMIT 1"
            )).first()
            if duplicate:
                raise RuntimeError(f"Resolve duplicate rows in {table} before applying {name}")
            op.create_unique_constraint(name, table, ["child_id", "lesson_id", "day_number"])

    if bind.dialect.name == "postgresql":
        op.alter_column("learning_evidence", "score", existing_type=sa.Integer(), nullable=True, server_default=None)


def downgrade():
    raise RuntimeError("Phase hardening downgrade can lose integrity and must be performed manually")
