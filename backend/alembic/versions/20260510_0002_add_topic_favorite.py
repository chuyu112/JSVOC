"""add topic favorite flag

Revision ID: 20260510_0002
Revises: 20260509_0001
Create Date: 2026-05-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260510_0002"
down_revision = "20260509_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "topics",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("topics", "is_favorite")
