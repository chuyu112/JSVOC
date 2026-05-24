"""add llm channels

Revision ID: 20260524_0011
Revises: 20260518_0010
Create Date: 2026-05-24 17:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260524_0011"
down_revision = "20260518_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_channels_id"), "llm_channels", ["id"], unique=False)
    op.create_index(op.f("ix_llm_channels_is_active"), "llm_channels", ["is_active"], unique=False)
    op.create_index(op.f("ix_llm_channels_provider"), "llm_channels", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_channels_provider"), table_name="llm_channels")
    op.drop_index(op.f("ix_llm_channels_is_active"), table_name="llm_channels")
    op.drop_index(op.f("ix_llm_channels_id"), table_name="llm_channels")
    op.drop_table("llm_channels")
