"""The `candidate_profiles` table (US-1.7).

One row per candidate, created lazily the first time the profile is read.
Lists such as skills/education/experience are stored as JSON columns: they are
read and written as a whole with the profile and never queried individually,
so separate tables would add joins for no benefit.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.mixins import TimestampMixin
from app.database.session import Base

if TYPE_CHECKING:
    from app.database.models.user import User


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    # The user id is both primary key and foreign key: exactly one profile per user.
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    education: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    experience: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    cv_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cv_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")
