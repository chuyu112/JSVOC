"""add project_reference_images table

Revision ID: 20260518_0009
Revises: 20260518_0008
Create Date: 2026-05-18 02:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260518_0009"
down_revision = "20260518_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_reference_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("reference_image_type", sa.String(length=20), nullable=False),
        sa.Column("source_image_base64", sa.Text(), nullable=False),
        sa.Column("source_image_mime", sa.String(length=80), nullable=False),
        sa.Column("source_image_filename", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_reference_images_id"), "project_reference_images", ["id"], unique=False)
    op.create_index(op.f("ix_project_reference_images_project_id"), "project_reference_images", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_reference_images_reference_image_type"), "project_reference_images", ["reference_image_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_reference_images_reference_image_type"), table_name="project_reference_images")
    op.drop_index(op.f("ix_project_reference_images_project_id"), table_name="project_reference_images")
    op.drop_index(op.f("ix_project_reference_images_id"), table_name="project_reference_images")
    op.drop_table("project_reference_images")
