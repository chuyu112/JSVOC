"""Add digital human tables.

Revision ID: 20260604_0014
Revises: 20260525_0013
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260604_0014"
down_revision = "20260525_0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "digital_human_avatars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("avatar_type", sa.String(length=20), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("gender", sa.String(length=10), nullable=True),
        sa.Column(
            "config_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_digital_human_avatars_avatar_type"),
        "digital_human_avatars",
        ["avatar_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_avatars_is_active"),
        "digital_human_avatars",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_avatars_name"),
        "digital_human_avatars",
        ["name"],
        unique=False,
    )

    op.create_table(
        "digital_human_voices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("voice_type", sa.String(length=20), nullable=False),
        sa.Column("sample_url", sa.String(length=500), nullable=True),
        sa.Column("gender", sa.String(length=10), nullable=True),
        sa.Column(
            "config_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_digital_human_voices_is_active"),
        "digital_human_voices",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_voices_name"),
        "digital_human_voices",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_voices_user_id"),
        "digital_human_voices",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_voices_voice_type"),
        "digital_human_voices",
        ["voice_type"],
        unique=False,
    )

    op.create_table(
        "digital_human_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("script_id", sa.Integer(), nullable=True),
        sa.Column("voice_id", sa.Integer(), nullable=True),
        sa.Column("avatar_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("audio_url", sa.String(length=500), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "config_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("credit_cost", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["avatar_id"],
            ["digital_human_avatars.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["script_id"],
            ["scripts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["generation_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["voice_id"],
            ["digital_human_voices.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_digital_human_videos_avatar_id"),
        "digital_human_videos",
        ["avatar_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_videos_project_id"),
        "digital_human_videos",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_videos_script_id"),
        "digital_human_videos",
        ["script_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_videos_status"),
        "digital_human_videos",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_human_videos_user_id"),
        "digital_human_videos",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("digital_human_videos")
    op.drop_table("digital_human_voices")
    op.drop_table("digital_human_avatars")
