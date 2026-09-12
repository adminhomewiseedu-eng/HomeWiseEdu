"""Add immutable quiz attempt grading snapshots.

Revision ID: 0011_quiz_attempts
Revises: 0010_provision_lesson_37_quiz
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_quiz_attempts"
down_revision = "0010_provision_lesson_37_quiz"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("score_percentage", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("submitted_answers", sa.JSON(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("score_percentage >= 0 AND score_percentage <= 100", name="ck_quiz_attempt_score_percentage"),
        sa.CheckConstraint("correct_count >= 0", name="ck_quiz_attempt_correct_count"),
        sa.CheckConstraint("total_questions >= 0", name="ck_quiz_attempt_total_questions"),
        sa.CheckConstraint("correct_count <= total_questions", name="ck_quiz_attempt_counts"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_quiz_attempts_submission_id", "quiz_attempts", ["submission_id"], unique=True)
    op.create_index(
        "ix_quiz_attempts_child_lesson_day_completed",
        "quiz_attempts",
        ["child_id", "lesson_id", "day_number", "completed_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_quiz_attempts_child_lesson_day_completed", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_submission_id", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
