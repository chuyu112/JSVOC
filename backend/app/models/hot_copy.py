from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utcnow_naive
from app.db.base import Base


class HotCopyMaterial(Base):
    __tablename__ = "hot_copy_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(40), nullable=False, default="douyin")
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="manual", index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_home_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    original_script: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict, nullable=False)
    analysis_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)


class HotCopyRewrite(Base):
    __tablename__ = "hot_copy_rewrites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("hot_copy_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    rewrite_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    duration: Mapped[str] = mapped_column(String(20), nullable=False)
    conversion_goal: Mapped[str] = mapped_column(String(80), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict, nullable=False)
    generation_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("generation_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
