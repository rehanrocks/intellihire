"""The `companies` table (US-1.3, US-3.x)."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.mixins import TimestampMixin
from app.database.session import Base

if TYPE_CHECKING:
    from app.database.models.user import User


class CompanyApprovalStatus(str, PyEnum):
    PENDING = "pending"    # registered, waiting for the platform admin (US-1.3)
    APPROVED = "approved"  # full access (US-12.4)
    REJECTED = "rejected"  # admin declined; reason stored below


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    official_email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    admin_contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    admin_contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Filled in later by the company administrator (US-3.1).
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    approval_status: Mapped[CompanyApprovalStatus] = mapped_column(
        Enum(CompanyApprovalStatus, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=CompanyApprovalStatus.PENDING,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    members: Mapped[list["User"]] = relationship("User", back_populates="company")

    def __repr__(self) -> str:
        return f"<Company {self.name} {self.approval_status.value}>"
