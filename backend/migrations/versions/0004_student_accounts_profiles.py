"""Add optional student accounts and child profile pictures.

Revision ID: 0004_student_accounts_profiles
Revises: 0003_curriculum_blueprint
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0004_student_accounts_profiles"
down_revision = "0003_curriculum_blueprint"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("children")}
    if "user_id" not in columns:
        op.add_column("children", sa.Column("user_id", sa.Integer(), nullable=True))
    if "profile_image_name" not in columns:
        op.add_column("children", sa.Column("profile_image_name", sa.String(), nullable=True))

    inspector = inspect(bind)
    foreign_keys = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("children")}
    indexes = {index.get("name") for index in inspector.get_indexes("children")}
    if bind.dialect.name != "sqlite" and "fk_children_user_id_users" not in foreign_keys:
        op.create_foreign_key("fk_children_user_id_users", "children", "users", ["user_id"], ["id"])
    if "ix_children_user_id" not in indexes:
        op.create_index("ix_children_user_id", "children", ["user_id"], unique=True)


def downgrade():
    op.drop_index("ix_children_user_id", table_name="children")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_children_user_id_users", "children", type_="foreignkey")
    op.drop_column("children", "profile_image_name")
    op.drop_column("children", "user_id")
