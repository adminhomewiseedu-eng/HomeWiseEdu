"""Add parent profiles.

Revision ID: 0007_parent_profiles
Revises: 0006_password_reset_tokens
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_parent_profiles"
down_revision = "0006_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "parent_profiles" in inspector.get_table_names():
        index_names = {index["name"] for index in inspector.get_indexes("parent_profiles")}
        if "ix_parent_profiles_user_id" not in index_names:
            op.create_index("ix_parent_profiles_user_id", "parent_profiles", ["user_id"], unique=True)
        return

    op.create_table(
        "parent_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("address_line_1", sa.String(), nullable=True),
        sa.Column("address_line_2", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state_region", sa.String(), nullable=True),
        sa.Column("postal_code", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("profile_image_name", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_parent_profiles_user_id"),
    )
    op.create_index("ix_parent_profiles_user_id", "parent_profiles", ["user_id"], unique=True)


def downgrade():
    op.drop_index("ix_parent_profiles_user_id", table_name="parent_profiles")
    op.drop_table("parent_profiles")
