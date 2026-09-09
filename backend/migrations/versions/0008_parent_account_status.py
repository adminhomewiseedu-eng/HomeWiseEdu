"""Add administratively controlled account status to users.

Revision ID: 0008_parent_account_status
Revises: 0007_parent_profiles
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_parent_account_status"
down_revision = "0007_parent_profiles"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "account_status" not in columns:
        op.add_column("users", sa.Column("account_status", sa.String(), nullable=False, server_default="active"))
    if "updated_at" not in columns:
        op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_check_constraint("ck_users_account_status", "users", "account_status IN ('active', 'suspended')")


def downgrade():
    op.drop_constraint("ck_users_account_status", "users", type_="check")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "account_status")
