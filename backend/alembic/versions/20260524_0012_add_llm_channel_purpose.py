"""add llm channel purpose

Revision ID: 20260524_0012
Revises: 20260524_0011
Create Date: 2026-05-24 20:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260524_0012"
down_revision = "20260524_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_channels",
        sa.Column("purpose", sa.String(length=40), nullable=False, server_default="chat"),
    )
    op.create_index(op.f("ix_llm_channels_purpose"), "llm_channels", ["purpose"], unique=False)
    op.alter_column("llm_channels", "purpose", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_channels_purpose"), table_name="llm_channels")
    op.drop_column("llm_channels", "purpose")
