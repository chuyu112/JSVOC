"""add user id to generation tasks

Revision ID: 20260515_0006
Revises: 20260515_0005
Create Date: 2026-05-15 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_0006"
down_revision = "20260515_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("generation_tasks", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_generation_tasks_user_id"), ["user_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_generation_tasks_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("generation_tasks", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_generation_tasks_user_id_users", type_="foreignkey")
        batch_op.drop_index(op.f("ix_generation_tasks_user_id"))
        batch_op.drop_column("user_id")
