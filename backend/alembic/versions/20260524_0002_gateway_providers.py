"""gateway providers

Revision ID: 20260524_0002
Revises: 20260509_0001
Create Date: 2026-05-24 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260524_0002"
down_revision = "20260509_0001"
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "gateway_providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("config", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gateway_providers_capability"), "gateway_providers", ["capability"], unique=False)
    op.create_index(op.f("ix_gateway_providers_id"), "gateway_providers", ["id"], unique=False)
    op.create_index(op.f("ix_gateway_providers_is_default"), "gateway_providers", ["is_default"], unique=False)
    op.create_index(op.f("ix_gateway_providers_is_enabled"), "gateway_providers", ["is_enabled"], unique=False)
    op.create_index(op.f("ix_gateway_providers_name"), "gateway_providers", ["name"], unique=False)
    op.create_index(op.f("ix_gateway_providers_provider"), "gateway_providers", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gateway_providers_provider"), table_name="gateway_providers")
    op.drop_index(op.f("ix_gateway_providers_name"), table_name="gateway_providers")
    op.drop_index(op.f("ix_gateway_providers_is_enabled"), table_name="gateway_providers")
    op.drop_index(op.f("ix_gateway_providers_is_default"), table_name="gateway_providers")
    op.drop_index(op.f("ix_gateway_providers_id"), table_name="gateway_providers")
    op.drop_index(op.f("ix_gateway_providers_capability"), table_name="gateway_providers")
    op.drop_table("gateway_providers")
