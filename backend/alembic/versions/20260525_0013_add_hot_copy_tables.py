"""add hot copy tables

Revision ID: 20260525_0013
Revises: 20260524_0012
Create Date: 2026-05-25 13:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0013"
down_revision = "20260524_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hot_copy_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("account_name", sa.String(length=120), nullable=True),
        sa.Column("account_home_url", sa.String(length=1000), nullable=True),
        sa.Column("cover_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("original_script", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("analysis_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hot_copy_materials_id"), "hot_copy_materials", ["id"], unique=False)
    op.create_index(op.f("ix_hot_copy_materials_project_id"), "hot_copy_materials", ["project_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_materials_source_type"), "hot_copy_materials", ["source_type"], unique=False)
    op.create_index(op.f("ix_hot_copy_materials_user_id"), "hot_copy_materials", ["user_id"], unique=False)

    op.create_table(
        "hot_copy_rewrites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("rewrite_mode", sa.String(length=40), nullable=False),
        sa.Column("duration", sa.String(length=20), nullable=False),
        sa.Column("conversion_goal", sa.String(length=80), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("generation_record_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["generation_record_id"], ["generation_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_id"], ["hot_copy_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hot_copy_rewrites_generation_record_id"), "hot_copy_rewrites", ["generation_record_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_id"), "hot_copy_rewrites", ["id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_material_id"), "hot_copy_rewrites", ["material_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_project_id"), "hot_copy_rewrites", ["project_id"], unique=False)
    op.create_index(op.f("ix_hot_copy_rewrites_user_id"), "hot_copy_rewrites", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hot_copy_rewrites_user_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_project_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_material_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_id"), table_name="hot_copy_rewrites")
    op.drop_index(op.f("ix_hot_copy_rewrites_generation_record_id"), table_name="hot_copy_rewrites")
    op.drop_table("hot_copy_rewrites")

    op.drop_index(op.f("ix_hot_copy_materials_user_id"), table_name="hot_copy_materials")
    op.drop_index(op.f("ix_hot_copy_materials_source_type"), table_name="hot_copy_materials")
    op.drop_index(op.f("ix_hot_copy_materials_project_id"), table_name="hot_copy_materials")
    op.drop_index(op.f("ix_hot_copy_materials_id"), table_name="hot_copy_materials")
    op.drop_table("hot_copy_materials")
