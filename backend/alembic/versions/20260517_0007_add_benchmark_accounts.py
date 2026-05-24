"""add benchmark_accounts to projects

Revision ID: 20260517_0007
Revises: cadc974eac25
Create Date: 2026-05-17 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260517_0007"
down_revision = "cadc974eac25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column("benchmark_accounts", sa.JSON(), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("projects", recreate="auto") as batch_op:
        batch_op.drop_column("benchmark_accounts")
