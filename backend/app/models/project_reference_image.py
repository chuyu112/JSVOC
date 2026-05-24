from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utcnow_naive
from app.db.base import Base


class ProjectReferenceImage(Base):
    __tablename__ = "project_reference_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_image_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    source_image_base64: Mapped[str] = mapped_column(Text, nullable=False)
    source_image_mime: Mapped[str] = mapped_column(String(80), nullable=False)
    source_image_filename: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow_naive,
        nullable=False,
    )
