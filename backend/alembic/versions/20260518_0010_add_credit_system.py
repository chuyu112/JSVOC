"""add credit system

Revision ID: 20260518_0010
Revises: 20260518_0009, cadc974eac25
Create Date: 2026-05-18 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260518_0010"
down_revision = ("20260518_0009", "cadc974eac25")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("total_granted", sa.Integer(), nullable=False),
        sa.Column("total_spent", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_credit_accounts_id"), "credit_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_credit_accounts_user_id"), "credit_accounts", ["user_id"], unique=True)

    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("reference_type", sa.String(length=80), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("transaction_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["credit_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transaction_type",
            "reference_type",
            "reference_id",
            name="uq_credit_transactions_type_reference",
        ),
    )
    op.create_index(op.f("ix_credit_transactions_account_id"), "credit_transactions", ["account_id"], unique=False)
    op.create_index(op.f("ix_credit_transactions_id"), "credit_transactions", ["id"], unique=False)
    op.create_index(op.f("ix_credit_transactions_reference_id"), "credit_transactions", ["reference_id"], unique=False)
    op.create_index(op.f("ix_credit_transactions_reference_type"), "credit_transactions", ["reference_type"], unique=False)
    op.create_index(op.f("ix_credit_transactions_transaction_type"), "credit_transactions", ["transaction_type"], unique=False)
    op.create_index(op.f("ix_credit_transactions_user_id"), "credit_transactions", ["user_id"], unique=False)

    op.add_column("generation_tasks", sa.Column("credit_cost", sa.Integer(), nullable=True))
    op.add_column("generation_tasks", sa.Column("credit_transaction_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("generation_tasks", "credit_transaction_id")
    op.drop_column("generation_tasks", "credit_cost")

    op.drop_index(op.f("ix_credit_transactions_user_id"), table_name="credit_transactions")
    op.drop_index(op.f("ix_credit_transactions_transaction_type"), table_name="credit_transactions")
    op.drop_index(op.f("ix_credit_transactions_reference_type"), table_name="credit_transactions")
    op.drop_index(op.f("ix_credit_transactions_reference_id"), table_name="credit_transactions")
    op.drop_index(op.f("ix_credit_transactions_id"), table_name="credit_transactions")
    op.drop_index(op.f("ix_credit_transactions_account_id"), table_name="credit_transactions")
    op.drop_table("credit_transactions")

    op.drop_index(op.f("ix_credit_accounts_user_id"), table_name="credit_accounts")
    op.drop_index(op.f("ix_credit_accounts_id"), table_name="credit_accounts")
    op.drop_table("credit_accounts")
