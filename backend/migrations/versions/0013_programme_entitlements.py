"""Add account programme entitlements.

Revision ID: 0013_programme_entitlements
Revises: 0012_curriculum_safety
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_programme_entitlements"
down_revision = "0012_curriculum_safety"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("programme", sa.String(), nullable=False, server_default="homeschool"),
    )
    op.execute("UPDATE users SET programme = 'homeschool' WHERE programme IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_check_constraint(
            "ck_users_programme",
            "programme IN ('homeschool', 'bible_study')",
        )


def downgrade():
    bind = op.get_bind()
    bible_accounts = bind.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE programme = 'bible_study'")
    ).scalar_one()
    if bible_accounts:
        raise RuntimeError(
            "Refusing to downgrade 0013_programme_entitlements: "
            "Bible Study accounts exist and removing users.programme would destroy "
            "their entitlement classification."
        )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_programme", type_="check")
    op.drop_column("users", "programme")
