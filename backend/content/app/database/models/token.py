"""Token tables.

`one_time_tokens` backs the links we email: verify-email (US-1.2) and
reset-password (US-1.6). Each row is single-use and has an expiry.

`revoked_tokens` is the logout list (US-1.5). A JWT is valid until it expires,
so to log someone out early we remember its id (jti) and refuse it.
Rows can be purged once `expires_at` has passed.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.database.session import Base


class TokenPurpose(str, PyEnum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class OneTimeToken(Base):
    __tablename__ = "one_time_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # SHA-256 hex digest of the random token (never the token itself).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    purpose: Mapped[TokenPurpose] = mapped_column(
        Enum(TokenPurpose, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return utcnow() > self.expires_at


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
