"""Protect curriculum history and add lesson safety state.

Revision ID: 0012_curriculum_safety
Revises: 0011_quiz_attempts
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_curriculum_safety"
down_revision = "0011_quiz_attempts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lessons", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("lessons", sa.Column("quiz_review_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.drop_constraint("quiz_attempts_lesson_id_fkey", "quiz_attempts", type_="foreignkey")
    op.create_foreign_key(
        "quiz_attempts_lesson_id_fkey",
        "quiz_attempts",
        "lessons",
        ["lesson_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_constraint("quiz_attempts_lesson_id_fkey", "quiz_attempts", type_="foreignkey")
    op.create_foreign_key(
        "quiz_attempts_lesson_id_fkey",
        "quiz_attempts",
        "lessons",
        ["lesson_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("lessons", "quiz_review_required")
    op.drop_column("lessons", "archived")
