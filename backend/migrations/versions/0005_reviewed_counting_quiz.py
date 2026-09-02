"""Provision the reviewed Counting to 5 quiz for imported curriculum lessons.

Revision ID: 0005_reviewed_counting_quiz
Revises: 0004_student_accounts_profiles
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_reviewed_counting_quiz"
down_revision = "0004_student_accounts_profiles"
branch_labels = None
depends_on = None


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


def upgrade():
    bind = op.get_bind()
    quiz_questions = sa.table(
        "quiz_questions",
        sa.column("lesson_id", sa.Integer()),
        sa.column("question", sa.String()),
        sa.column("options", sa.JSON()),
        sa.column("correct_answer", sa.String()),
        sa.column("explanation_correct", sa.String()),
        sa.column("explanation_incorrect", sa.String()),
    )
    lesson_ids = bind.execute(sa.text(
        "SELECT id FROM lessons WHERE lower(trim(topic)) = 'counting to 5'"
    )).scalars().all()

    for lesson_id in lesson_ids:
        existing = bind.execute(sa.text(
            "SELECT COUNT(*) FROM quiz_questions WHERE lesson_id = :lesson_id"
        ), {"lesson_id": lesson_id}).scalar_one()
        if existing:
            continue
        bind.execute(sa.insert(quiz_questions), [{
                "lesson_id": lesson_id,
                "question": item["question"],
                "options": item["options"],
                "correct_answer": item["correct_answer"],
                "explanation_correct": item["explanation_correct"],
                "explanation_incorrect": item["explanation_incorrect"],
            } for item in REVIEWED_QUESTIONS])


def downgrade():
    bind = op.get_bind()
    for item in REVIEWED_QUESTIONS:
        bind.execute(sa.text(
            """DELETE FROM quiz_questions
               WHERE question = :question
                 AND lesson_id IN (SELECT id FROM lessons WHERE lower(trim(topic)) = 'counting to 5')"""
        ), {"question": item["question"]})
