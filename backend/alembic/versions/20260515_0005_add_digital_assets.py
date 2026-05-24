"""add digital assets

Revision ID: 20260515_0005
Revises: 20260514_0004
Create Date: 2026-05-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0005"
down_revision = "20260514_0004"
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "digital_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("project_snapshot", json_type, nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("generation_record_id", sa.Integer(), nullable=True),
        sa.Column("oss_object_key", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("asset_metadata", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["generation_record_id"], ["generation_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_digital_assets_asset_type"), "digital_assets", ["asset_type"], unique=False)
    op.create_index(op.f("ix_digital_assets_generation_record_id"), "digital_assets", ["generation_record_id"], unique=False)
    op.create_index(op.f("ix_digital_assets_id"), "digital_assets", ["id"], unique=False)
    op.create_index(op.f("ix_digital_assets_source_project_id"), "digital_assets", ["source_project_id"], unique=False)
    op.create_index(op.f("ix_digital_assets_user_id"), "digital_assets", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_digital_assets_user_id"), table_name="digital_assets")
    op.drop_index(op.f("ix_digital_assets_source_project_id"), table_name="digital_assets")
    op.drop_index(op.f("ix_digital_assets_id"), table_name="digital_assets")
    op.drop_index(op.f("ix_digital_assets_generation_record_id"), table_name="digital_assets")
    op.drop_index(op.f("ix_digital_assets_asset_type"), table_name="digital_assets")
    op.drop_table("digital_assets")
