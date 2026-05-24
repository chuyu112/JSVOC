"""add benchmark_samples to projects

Revision ID: 20260518_0008
Revises: 20260517_0007
Create Date: 2026-05-18 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260518_0008"
down_revision = "20260517_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column("benchmark_samples", sa.JSON(), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("projects", recreate="auto") as batch_op:
        batch_op.drop_column("benchmark_samples")
