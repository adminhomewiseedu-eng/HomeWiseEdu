"""Persist authoritative curriculum blueprint metadata.

Revision ID: 0003_curriculum_blueprint
Revises: 0002_phase_hardening
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_curriculum_blueprint"
down_revision = "0002_phase_hardening"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    lesson_columns = {c["name"] for c in inspector.get_columns("lessons")}
    day_columns = {c["name"] for c in inspector.get_columns("lesson_days")}
    if "curriculum_country" not in lesson_columns:
        op.add_column("lessons", sa.Column("curriculum_country", sa.String(), nullable=True))
    if "origin_of_knowledge" not in day_columns:
        op.add_column("lesson_days", sa.Column("origin_of_knowledge", sa.Text(), nullable=True))
    if "video_url" not in day_columns:
        op.add_column("lesson_days", sa.Column("video_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("lesson_days", "video_url")
    op.drop_column("lesson_days", "origin_of_knowledge")
    op.drop_column("lessons", "curriculum_country")
