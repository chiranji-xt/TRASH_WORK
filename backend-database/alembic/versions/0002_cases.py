"""Cases tables: groups duplicate reports of the same real-world pile.

Revision ID: 0002_cases
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision = "0002_cases"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("first_reported_at", sa.DateTime(), nullable=True),
        sa.Column("last_reported_at", sa.DateTime(), nullable=True),
        sa.Column("report_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_reporters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recurrence_of", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("suggested_duplicate_of", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "case_merge_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("garbage_reports.id"), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.add_column("garbage_reports", sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True))
    op.create_index("ix_garbage_reports_case_id", "garbage_reports", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_garbage_reports_case_id", table_name="garbage_reports")
    op.drop_column("garbage_reports", "case_id")
    op.drop_table("case_merge_log")
    op.drop_table("cases")
