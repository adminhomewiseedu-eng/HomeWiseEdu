"""Add secure password reset tokens and JWT invalidation version.

Revision ID: 0006_password_reset_tokens
Revises: 0005_reviewed_counting_quiz
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0006_password_reset_tokens"
down_revision = "0005_reviewed_counting_quiz"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "auth_version" not in user_columns:
        op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    if "password_reset_tokens" not in inspector.get_table_names():
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
        op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])


def downgrade():
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "auth_version")
