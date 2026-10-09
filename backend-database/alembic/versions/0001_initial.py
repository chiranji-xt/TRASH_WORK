"""Consolidated initial schema (replaces the three one-off scripts).

Revision ID: 0001_initial
Replaces: init_db.py, migrate_db.py, add_status_column_migration.py,
          add_boxed_column_migration.py (see database setup/README.md).
"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "garbage_reports",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("image_path", sa.String(), nullable=False),
        sa.Column("boxed_image_path", sa.String(), nullable=True),
        sa.Column("prediction", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("detections", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("garbage_reports")
