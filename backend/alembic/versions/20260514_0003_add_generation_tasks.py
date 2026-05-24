"""add generation tasks

Revision ID: 20260514_0003
Revises: 20260510_0002
Create Date: 2026-05-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0003"
down_revision = "20260510_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_generation_tasks_id"), "generation_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_generation_tasks_project_id"), "generation_tasks", ["project_id"], unique=False)
    op.create_index(op.f("ix_generation_tasks_status"), "generation_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_generation_tasks_task_type"), "generation_tasks", ["task_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generation_tasks_task_type"), table_name="generation_tasks")
    op.drop_index(op.f("ix_generation_tasks_status"), table_name="generation_tasks")
    op.drop_index(op.f("ix_generation_tasks_project_id"), table_name="generation_tasks")
    op.drop_index(op.f("ix_generation_tasks_id"), table_name="generation_tasks")
    op.drop_table("generation_tasks")
