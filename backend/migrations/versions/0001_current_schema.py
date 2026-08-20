"""Initial schema for new HomeWiseEdu databases.

Revision ID: 0001_current_schema
"""
from alembic import op

from backend.database import Base
from backend import models  # noqa: F401

revision = "0001_current_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # This baseline creates the complete current schema on a clean database.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    # Deliberately refuse a bulk destructive downgrade in production.
    raise RuntimeError("The initial HomeWiseEdu schema downgrade is destructive and must be performed manually")
