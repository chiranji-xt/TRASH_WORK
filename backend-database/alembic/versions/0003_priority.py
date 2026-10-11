"""Priority score bookkeeping on cases.

Revision ID: 0003_priority
Revises: 0002_cases
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_priority"
down_revision = "0002_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("score_version", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "score_version")
