"""Add optional student accounts and child profile pictures.

Revision ID: 0004_student_accounts_profiles
Revises: 0003_curriculum_blueprint
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_student_accounts_profiles"
down_revision = "0003_curriculum_blueprint"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("children", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("children", sa.Column("profile_image_name", sa.String(), nullable=True))
    op.create_foreign_key("fk_children_user_id_users", "children", "users", ["user_id"], ["id"])
    op.create_index("ix_children_user_id", "children", ["user_id"], unique=True)


def downgrade():
    op.drop_index("ix_children_user_id", table_name="children")
    op.drop_constraint("fk_children_user_id_users", "children", type_="foreignkey")
    op.drop_column("children", "profile_image_name")
    op.drop_column("children", "user_id")
