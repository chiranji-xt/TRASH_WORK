"""Cleanup verification tables.

Revision ID: 0004_verification
Revises: 0003_priority
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_verification"
down_revision = "0003_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cleanup_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("cleaner_id", sa.String(), nullable=True),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("photos", sa.JSON(), nullable=True),
        sa.Column("checks", sa.JSON(), nullable=True),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("spot_checked", sa.String(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_cleanup_verifications_case_id", "cleanup_verifications", ["case_id"])
    op.add_column("cases", sa.Column("closed_at", sa.DateTime(), nullable=True))
    op.add_column("cases", sa.Column("closing_verification_id",
                                     sa.Integer(), sa.ForeignKey("cleanup_verifications.id"),
                                     nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "closing_verification_id")
    op.drop_column("cases", "closed_at")
    op.drop_index("ix_cleanup_verifications_case_id", table_name="cleanup_verifications")
    op.drop_table("cleanup_verifications")
