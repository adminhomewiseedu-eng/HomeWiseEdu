"""Add optional authored weeks and durable parent plans without changing progress."""
import sqlalchemy as sa
from alembic import op

revision = "0014_lesson_assignments"
down_revision = "0013_programme_entitlements"
branch_labels = depends_on = None


def upgrade():
    op.add_column("lessons", sa.Column("curriculum_week", sa.Integer(), nullable=True))
    with op.batch_alter_table("lessons") as batch:
        batch.create_check_constraint("ck_lesson_curriculum_week", "curriculum_week IS NULL OR curriculum_week > 0")
    op.create_table(
        "lesson_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scheduled_date", sa.String(10), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancelled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("day_number > 0 AND priority >= 0", name="ck_assignment_position"),
    )
    op.create_index("ix_lesson_assignments_child_id", "lesson_assignments", ["child_id"])
    op.create_index("ix_lesson_assignments_lesson_id", "lesson_assignments", ["lesson_id"])
    op.create_index("uq_child_assignment_date", "lesson_assignments",
                    ["child_id", "lesson_id", "day_number", "scheduled_date"], unique=True,
                    postgresql_where=sa.text("cancelled = false"), sqlite_where=sa.text("cancelled = 0"))


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM lesson_assignments")).scalar_one() or bind.execute(
        sa.text("SELECT COUNT(*) FROM lessons WHERE curriculum_week IS NOT NULL")
    ).scalar_one():
        raise RuntimeError("Refusing downgrade: assignments or authored curriculum weeks would be lost")
    op.drop_table("lesson_assignments")
    with op.batch_alter_table("lessons") as batch:
        batch.drop_constraint("ck_lesson_curriculum_week", type_="check")
        batch.drop_column("curriculum_week")
