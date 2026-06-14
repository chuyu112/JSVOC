"""Seed digital human preset avatars and voices.

Revision ID: 20260604_0015
Revises: 20260604_0014
Create Date: 2026-06-04
"""

from alembic import op
from sqlalchemy import table, column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# revision identifiers, used by Alembic.
revision = "20260604_0015"
down_revision = "20260604_0014"
branch_labels = None
depends_on = None


def upgrade():
    avatars = table(
        "digital_human_avatars",
        column("id", Integer),
        column("name", String),
        column("avatar_type", String),
        column("thumbnail_url", String),
        column("video_url", String),
        column("gender", String),
        column("config_json", JSONB),
        column("is_active", Integer),
        column("created_at", DateTime),
    )

    voices = table(
        "digital_human_voices",
        column("id", Integer),
        column("user_id", Integer),
        column("name", String),
        column("voice_type", String),
        column("sample_url", String),
        column("gender", String),
        column("config_json", JSONB),
        column("is_active", Integer),
        column("created_at", DateTime),
    )

    now = datetime.utcnow()

    op.bulk_insert(
        avatars,
        [
            {
                "id": 1,
                "name": "翡翠专家-女",
                "avatar_type": "preset",
                "thumbnail_url": None,
                "video_url": None,
                "gender": "female",
                "config_json": {"description": "专业女性形象，适合翡翠知识讲解"},
                "is_active": 1,
                "created_at": now,
            },
            {
                "id": 2,
                "name": "翡翠专家-男",
                "avatar_type": "preset",
                "thumbnail_url": None,
                "video_url": None,
                "gender": "male",
                "config_json": {"description": "专业男性形象，适合翡翠知识讲解"},
                "is_active": 1,
                "created_at": now,
            },
            {
                "id": 3,
                "name": "老板娘",
                "avatar_type": "preset",
                "thumbnail_url": None,
                "video_url": None,
                "gender": "female",
                "config_json": {"description": "亲和力强的女性形象，适合带货口播"},
                "is_active": 1,
                "created_at": now,
            },
            {
                "id": 4,
                "name": "老板",
                "avatar_type": "preset",
                "thumbnail_url": None,
                "video_url": None,
                "gender": "male",
                "config_json": {"description": "沉稳男性形象，适合信任建立类内容"},
                "is_active": 1,
                "created_at": now,
            },
        ],
    )

    op.bulk_insert(
        voices,
        [
            {
                "id": 1,
                "user_id": None,
                "name": "温柔女声",
                "voice_type": "preset",
                "sample_url": None,
                "gender": "female",
                "config_json": {"description": "温柔亲和的女性声音"},
                "is_active": 1,
                "created_at": now,
            },
            {
                "id": 2,
                "user_id": None,
                "name": "沉稳男声",
                "voice_type": "preset",
                "sample_url": None,
                "gender": "male",
                "config_json": {"description": "沉稳专业的男性声音"},
                "is_active": 1,
                "created_at": now,
            },
            {
                "id": 3,
                "user_id": None,
                "name": "活泼女声",
                "voice_type": "preset",
                "sample_url": None,
                "gender": "female",
                "config_json": {"description": "活泼热情的女性声音，适合带货"},
                "is_active": 1,
                "created_at": now,
            },
        ],
    )


def downgrade():
    op.execute("DELETE FROM digital_human_voices WHERE voice_type = 'preset'")
    op.execute("DELETE FROM digital_human_avatars WHERE avatar_type = 'preset'")
