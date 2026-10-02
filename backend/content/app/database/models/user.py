"""The `users` table.

Every person who can log in is a row here, whatever their role. Role-specific
data lives in other tables (candidate_profiles for candidates, companies for
company staff) and links back with a foreign key.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import Role
from app.database.models.mixins import TimestampMixin
from app.database.session import Base

if TYPE_CHECKING:  # avoids circular imports at runtime, still gives type hints
    from app.database.models.company import Company
    from app.database.models.profile import CandidateProfile


class UserStatus(str, PyEnum):
    PENDING_VERIFICATION = "pending_verification"  # registered, email not yet confirmed (US-1.1)
    ACTIVE = "active"
    SUSPENDED = "suspended"                        # blocked by platform admin (US-12.6)


def _enum(enum_cls):
    # Store the enum *values* ("candidate") as plain VARCHAR so SQLite and
    # PostgreSQL behave the same and the data stays readable in any DB tool.
    return Enum(enum_cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(_enum(Role), nullable=False, default=Role.CANDIDATE)
    status: Mapped[UserStatus] = mapped_column(_enum(UserStatus), nullable=False, default=UserStatus.PENDING_VERIFICATION)

    # Only company staff have a company. ondelete="SET NULL": deleting a
    # company does not delete its people, it just unlinks them.
    company_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Any JWT issued before this moment is rejected, so a password reset logs
    # out every existing session.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="members")
    profile: Mapped["CandidateProfile | None"] = relationship(
        "CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # handy when debugging
        return f"<User {self.email} role={self.role.value} status={self.status.value}>"
