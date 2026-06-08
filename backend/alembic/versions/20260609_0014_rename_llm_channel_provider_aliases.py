"""rename llm channel provider aliases

Revision ID: 20260609_0014
Revises: 20260525_0013
Create Date: 2026-06-09 04:30:00
"""

from alembic import op


revision = "20260609_0014"
down_revision = "20260525_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE llm_channels SET provider = 'moyu_image' WHERE provider IN ('moyu-pic', 'moyu_pic')")
    op.execute("UPDATE llm_channels SET provider = 'seedance_video' WHERE provider IN ('ark-video', 'ark_video')")


def downgrade() -> None:
    op.execute("UPDATE llm_channels SET provider = 'moyu_pic' WHERE provider = 'moyu_image'")
    op.execute("UPDATE llm_channels SET provider = 'ark_video' WHERE provider = 'seedance_video'")
