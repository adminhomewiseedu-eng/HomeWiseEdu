"""Add personal profiles for administrator accounts.

Revision ID: 0009_admin_profiles
Revises: 0008_parent_account_status
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_admin_profiles"
down_revision = "0008_parent_account_status"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_profiles",
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
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_admin_profiles_user_id"),
    )
    op.create_index("ix_admin_profiles_user_id", "admin_profiles", ["user_id"], unique=True)


def downgrade():
    op.drop_index("ix_admin_profiles_user_id", table_name="admin_profiles")
    op.drop_table("admin_profiles")
