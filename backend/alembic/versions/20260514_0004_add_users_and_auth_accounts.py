"""add users and auth accounts

Revision ID: 20260514_0004
Revises: 20260514_0003
Create Date: 2026-05-14 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0004"
down_revision = "20260514_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "auth_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=40), nullable=False),
        sa.Column("provider_key", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_type", "provider_key", name="uq_auth_accounts_provider_identity"),
    )
    op.create_index(op.f("ix_auth_accounts_id"), "auth_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_auth_accounts_provider_key"), "auth_accounts", ["provider_key"], unique=False)
    op.create_index(op.f("ix_auth_accounts_provider_type"), "auth_accounts", ["provider_type"], unique=False)
    op.create_index(op.f("ix_auth_accounts_user_id"), "auth_accounts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_accounts_user_id"), table_name="auth_accounts")
    op.drop_index(op.f("ix_auth_accounts_provider_type"), table_name="auth_accounts")
    op.drop_index(op.f("ix_auth_accounts_provider_key"), table_name="auth_accounts")
    op.drop_index(op.f("ix_auth_accounts_id"), table_name="auth_accounts")
    op.drop_table("auth_accounts")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
