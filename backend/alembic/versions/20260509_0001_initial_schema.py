"""initial schema

Revision ID: 20260509_0001
Revises:
Create Date: 2026-05-09 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260509_0001"
down_revision = None
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("project_name", sa.String(length=120), nullable=False),
        sa.Column("industry", sa.String(length=80), nullable=False),
        sa.Column("sub_industry", sa.String(length=120), nullable=True),
        sa.Column("product", sa.String(length=200), nullable=False),
        sa.Column("personal_intro", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("platforms", json_type, nullable=False),
        sa.Column("current_stage", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_project_name"), "projects", ["project_name"], unique=False)
    op.create_index(op.f("ix_projects_user_id"), "projects", ["user_id"], unique=False)

    op.create_table(
        "generation_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("module_name", sa.String(length=80), nullable=False),
        sa.Column("input_data", json_type, nullable=False),
        sa.Column("output_data", json_type, nullable=False),
        sa.Column("model_provider", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=True),
        sa.Column("token_usage", json_type, nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_generation_records_id"), "generation_records", ["id"], unique=False)
    op.create_index(op.f("ix_generation_records_module_name"), "generation_records", ["module_name"], unique=False)
    op.create_index(op.f("ix_generation_records_project_id"), "generation_records", ["project_id"], unique=False)
    op.create_index(op.f("ix_generation_records_user_id"), "generation_records", ["user_id"], unique=False)

    op.create_table(
        "account_strategy_contexts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("generation_record_id", sa.Integer(), nullable=True),
        sa.Column("account_positioning", sa.Text(), nullable=False),
        sa.Column("persona", sa.Text(), nullable=False),
        sa.Column("target_user_profile", json_type, nullable=False),
        sa.Column("account_names", json_type, nullable=False),
        sa.Column("bios", json_type, nullable=False),
        sa.Column("content_columns", json_type, nullable=False),
        sa.Column("trust_design", json_type, nullable=False),
        sa.Column("conversion_path", json_type, nullable=False),
        sa.Column("platform_strategies", json_type, nullable=False),
        sa.Column("content_style", sa.String(length=120), nullable=True),
        sa.Column("trust_points", json_type, nullable=False),
        sa.Column("monetization_paths", json_type, nullable=False),
        sa.Column("execution_stage", sa.String(length=80), nullable=True),
        sa.Column("context_data", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["generation_record_id"], ["generation_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_strategy_contexts_generation_record_id"), "account_strategy_contexts", ["generation_record_id"], unique=False)
    op.create_index(op.f("ix_account_strategy_contexts_id"), "account_strategy_contexts", ["id"], unique=False)
    op.create_index(op.f("ix_account_strategy_contexts_project_id"), "account_strategy_contexts", ["project_id"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("goal", sa.String(length=80), nullable=False),
        sa.Column("selling_point", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("topic_data", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topics_goal"), "topics", ["goal"], unique=False)
    op.create_index(op.f("ix_topics_id"), "topics", ["id"], unique=False)
    op.create_index(op.f("ix_topics_platform"), "topics", ["platform"], unique=False)
    op.create_index(op.f("ix_topics_project_id"), "topics", ["project_id"], unique=False)
    op.create_index(op.f("ix_topics_title"), "topics", ["title"], unique=False)

    op.create_table(
        "scripts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("script_type", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("script_content", sa.Text(), nullable=False),
        sa.Column("shot_suggestions", json_type, nullable=False),
        sa.Column("conversion_script", sa.Text(), nullable=False),
        sa.Column("script_data", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scripts_id"), "scripts", ["id"], unique=False)
    op.create_index(op.f("ix_scripts_platform"), "scripts", ["platform"], unique=False)
    op.create_index(op.f("ix_scripts_project_id"), "scripts", ["project_id"], unique=False)
    op.create_index(op.f("ix_scripts_title"), "scripts", ["title"], unique=False)
    op.create_index(op.f("ix_scripts_topic_id"), "scripts", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scripts_topic_id"), table_name="scripts")
    op.drop_index(op.f("ix_scripts_title"), table_name="scripts")
    op.drop_index(op.f("ix_scripts_project_id"), table_name="scripts")
    op.drop_index(op.f("ix_scripts_platform"), table_name="scripts")
    op.drop_index(op.f("ix_scripts_id"), table_name="scripts")
    op.drop_table("scripts")

    op.drop_index(op.f("ix_topics_title"), table_name="topics")
    op.drop_index(op.f("ix_topics_project_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_platform"), table_name="topics")
    op.drop_index(op.f("ix_topics_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_goal"), table_name="topics")
    op.drop_table("topics")

    op.drop_index(op.f("ix_account_strategy_contexts_project_id"), table_name="account_strategy_contexts")
    op.drop_index(op.f("ix_account_strategy_contexts_id"), table_name="account_strategy_contexts")
    op.drop_index(op.f("ix_account_strategy_contexts_generation_record_id"), table_name="account_strategy_contexts")
    op.drop_table("account_strategy_contexts")

    op.drop_index(op.f("ix_generation_records_user_id"), table_name="generation_records")
    op.drop_index(op.f("ix_generation_records_project_id"), table_name="generation_records")
    op.drop_index(op.f("ix_generation_records_module_name"), table_name="generation_records")
    op.drop_index(op.f("ix_generation_records_id"), table_name="generation_records")
    op.drop_table("generation_records")

    op.drop_index(op.f("ix_projects_user_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_project_name"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
