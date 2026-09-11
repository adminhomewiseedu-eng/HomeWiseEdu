"""Provision the reviewed Counting to 5 quiz for curriculum lesson 37.

Revision ID: 0010_provision_lesson_37_quiz
Revises: 0009_admin_profiles
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_provision_lesson_37_quiz"
down_revision = "0009_admin_profiles"
branch_labels = None
depends_on = None


LESSON_ID = 37
EXPECTED_IDENTITY = {
    "level": 0,
    "subject": "mathematics",
    "unit": "number sense",
    "topic": "counting to 5",
}

REVIEWED_QUESTIONS = (
    {
        "question": "How many stars are here: ⭐ ⭐ ⭐?",
        "options": ["2", "3", "4", "5"],
        "correct_answer": "3",
        "explanation_correct": "Spot on! There are 3 stars! ⭐⭐⭐",
        "explanation_incorrect": "Count them one by one: 1, 2, 3!",
    },
    {
        "question": "Which number comes directly after 4?",
        "options": ["3", "5", "2", "6"],
        "correct_answer": "5",
        "explanation_correct": "Awesome! 5 comes right after 4! 🌟",
        "explanation_incorrect": "Let's count: 1, 2, 3, 4, 5!",
    },
    {
        "question": "How many fingers are on one hand?",
        "options": ["4", "5", "6", "3"],
        "correct_answer": "5",
        "explanation_correct": "Yay! 5 fingers on one hand! ✋",
        "explanation_incorrect": "Count your fingers on one hand: 1, 2, 3, 4, 5!",
    },
)


def _normalized(value):
    return " ".join((value or "").strip().lower().split())


def _verify_lesson_identity(bind):
    row = bind.execute(sa.text(
        """SELECT l.id, l.level, l.topic, u.title AS unit_title, s.title AS subject_title
           FROM lessons AS l
           JOIN units AS u ON u.id = l.unit_id
           JOIN subjects AS s ON s.id = u.subject_id
           WHERE l.id = :lesson_id"""
    ), {"lesson_id": LESSON_ID}).mappings().one_or_none()

    if row is None:
        raise RuntimeError("Refusing to provision quiz: lesson 37 does not exist")

    actual = {
        "level": row["level"],
        "subject": _normalized(row["subject_title"]),
        "unit": _normalized(row["unit_title"]),
        "topic": _normalized(row["topic"]),
    }
    if actual != EXPECTED_IDENTITY:
        raise RuntimeError(
            "Refusing to provision quiz: lesson 37 identity does not match "
            "Level 0 / Mathematics / Number Sense / Counting to 5"
        )


def upgrade():
    bind = op.get_bind()
    _verify_lesson_identity(bind)
    quiz_questions = sa.table(
        "quiz_questions",
        sa.column("lesson_id", sa.Integer()),
        sa.column("question", sa.String()),
        sa.column("options", sa.JSON()),
        sa.column("correct_answer", sa.String()),
        sa.column("explanation_correct", sa.String()),
        sa.column("explanation_incorrect", sa.String()),
    )

    for item in REVIEWED_QUESTIONS:
        exists = bind.execute(sa.text(
            """SELECT 1 FROM quiz_questions
               WHERE lesson_id = :lesson_id AND question = :question"""
        ), {"lesson_id": LESSON_ID, "question": item["question"]}).first()
        if exists:
            continue
        bind.execute(sa.insert(quiz_questions), {
            "lesson_id": LESSON_ID,
            **item,
        })


def downgrade():
    # Deliberately non-destructive: these are approved curriculum records and
    # may have existed before this idempotent migration was applied.
    pass
