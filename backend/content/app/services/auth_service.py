"""Authentication business rules (US-1.1 to US-1.6, plus company approval US-12.4).

Read the functions top to bottom and you have the whole login lifecycle:
register -> verify email -> log in -> (log out) -> forgot/reset password.
"""
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    AccountNotVerified,
    AccountSuspended,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    NotFound,
    TokenExpired,
)
from app.core.permissions import DASHBOARD_BY_ROLE, Role
from app.core.security import create_access_token, generate_one_time_token, hash_password, hash_token, verify_password
from app.core.time import from_timestamp, utcnow
from app.database.models import Company, CompanyApprovalStatus, OneTimeToken, RevokedToken, TokenPurpose, User, UserStatus
from app.schemas.auth import RegisterCompanyRequest, RegisterIndividualRequest
from app.services import email_service

logger = logging.getLogger(__name__)

# Used to spend the same time on "unknown email" as on "wrong password", so an
# attacker cannot tell which emails exist by measuring response time.
_DUMMY_HASH = hash_password("timing-equaliser")


# ----------------------------------------------------------------------------
# Lookups
# ----------------------------------------------------------------------------
def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def _email_taken(db: Session, email: str) -> bool:
    email = email.strip().lower()
    if get_user_by_email(db, email) is not None:
        return True
    return db.scalar(select(Company).where(Company.official_email == email)) is not None


# ----------------------------------------------------------------------------
# One-time tokens
# ----------------------------------------------------------------------------
def _issue_one_time_token(db: Session, user: User, purpose: TokenPurpose, lifetime: timedelta) -> str:
    """Invalidate older tokens of the same purpose, create a fresh one, return the raw token."""
    now = utcnow()
    for old in db.scalars(select(OneTimeToken).where(OneTimeToken.user_id == user.id, OneTimeToken.purpose == purpose, OneTimeToken.used_at.is_(None))):
        old.used_at = now
    raw = generate_one_time_token()
    db.add(OneTimeToken(user_id=user.id, token_hash=hash_token(raw), purpose=purpose, expires_at=now + lifetime))
    return raw


def _consume_one_time_token(db: Session, raw_token: str, purpose: TokenPurpose) -> OneTimeToken:
    token = db.scalar(select(OneTimeToken).where(OneTimeToken.token_hash == hash_token(raw_token), OneTimeToken.purpose == purpose))
    if token is None or token.is_used:
        raise InvalidToken()
    if token.is_expired:
        raise TokenExpired()
    token.used_at = utcnow()
    return token


# ----------------------------------------------------------------------------
# US-1.1 / US-1.2  Individual registration and email verification
# ----------------------------------------------------------------------------
def register_individual(db: Session, data: RegisterIndividualRequest) -> User:
    if _email_taken(db, data.email):
        raise EmailAlreadyRegistered()

    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=Role.CANDIDATE,
        status=UserStatus.PENDING_VERIFICATION,
    )
    db.add(user)
    db.flush()  # assigns user.id without committing yet

    raw_token = _issue_one_time_token(db, user, TokenPurpose.EMAIL_VERIFICATION, timedelta(hours=get_settings().email_verification_expire_hours))
    db.commit()
    db.refresh(user)

    # Send after commit: if the email provider is slow or down, the account still exists
    # and the user can ask for the link again (US-1.2).
    try:
        email_service.send_verification_email(user.email, user.full_name, raw_token)
    except Exception:  # pragma: no cover - depends on external provider
        logger.exception("Could not send verification email to %s", user.email)
    return user


def verify_email(db: Session, raw_token: str) -> User:
    token = _consume_one_time_token(db, raw_token, TokenPurpose.EMAIL_VERIFICATION)
    user = db.get(User, token.user_id)
    if user is None:
        raise InvalidToken()
    if user.status == UserStatus.PENDING_VERIFICATION:
        user.status = UserStatus.ACTIVE
    db.commit()
    return user


def resend_verification(db: Session, email: str) -> None:
    """Always succeeds from the caller's point of view (no account enumeration)."""
    user = get_user_by_email(db, email)
    if user is None or user.status != UserStatus.PENDING_VERIFICATION:
        return
    raw_token = _issue_one_time_token(db, user, TokenPurpose.EMAIL_VERIFICATION, timedelta(hours=get_settings().email_verification_expire_hours))
    db.commit()
    email_service.send_verification_email(user.email, user.full_name, raw_token)


# ----------------------------------------------------------------------------
# US-1.3  Company registration (+ US-12.4 approval decision)
# ----------------------------------------------------------------------------
def register_company(db: Session, data: RegisterCompanyRequest) -> tuple[Company, User]:
    if _email_taken(db, data.official_email):
        raise EmailAlreadyRegistered()

    company = Company(
        name=data.company_name.strip(),
        industry=data.industry.strip(),
        official_email=data.official_email,
        admin_contact_name=data.admin_full_name.strip(),
        admin_contact_phone=data.admin_contact_phone,
        approval_status=CompanyApprovalStatus.PENDING,
    )
    db.add(company)
    db.flush()

    # The company administrator can log in straight away (to see the pending
    # status), but every company feature is gated until approval.
    admin = User(
        email=data.official_email,
        full_name=data.admin_full_name.strip(),
        password_hash=hash_password(data.password),
        role=Role.COMPANY_ADMIN,
        status=UserStatus.ACTIVE,
        company_id=company.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(company)
    db.refresh(admin)

    try:
        email_service.send_company_registration_received(admin.email, company.name)
    except Exception:  # pragma: no cover
        logger.exception("Could not send company registration email to %s", admin.email)
    return company, admin


def decide_company(db: Session, company_id, approve: bool, reason: str | None) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFound("Company not found")
    if approve:
        company.approval_status = CompanyApprovalStatus.APPROVED
        company.approved_at = utcnow()
        company.rejection_reason = None
    else:
        company.approval_status = CompanyApprovalStatus.REJECTED
        company.rejection_reason = reason
    db.commit()
    db.refresh(company)
    email_service.send_company_decision(company.official_email, company.name, approve, reason)
    return company


# ----------------------------------------------------------------------------
# US-1.4 / US-1.5  Login and logout
# ----------------------------------------------------------------------------
def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)  # constant-time behaviour
        raise InvalidCredentials()
    if not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    # Only after the password matched do we reveal anything about the account state.
    if user.status == UserStatus.PENDING_VERIFICATION:
        raise AccountNotVerified()
    if user.status == UserStatus.SUSPENDED:
        raise AccountSuspended()
    return user


def login(db: Session, email: str, password: str) -> tuple[str, "datetime", User, str]:
    user = authenticate(db, email, password)
    user.last_login_at = utcnow()
    db.commit()
    token, _jti, expires_at = create_access_token(user_id=user.id, role=user.role.value)
    return token, expires_at, user, DASHBOARD_BY_ROLE[user.role]


def logout(db: Session, user: User, token_payload: dict) -> None:
    """Put the token's jti on the deny list until it would have expired anyway."""
    jti = token_payload.get("jti")
    exp = token_payload.get("exp")
    if not jti or not exp:
        return
    if db.get(RevokedToken, jti) is None:
        db.add(RevokedToken(jti=jti, user_id=user.id, expires_at=from_timestamp(exp)))
        db.commit()


# ----------------------------------------------------------------------------
# US-1.6  Password recovery
# ----------------------------------------------------------------------------
def request_password_reset(db: Session, email: str) -> None:
    """Neutral by design: the response is identical whether or not the email exists."""
    user = get_user_by_email(db, email)
    if user is None or user.status == UserStatus.SUSPENDED:
        return
    raw_token = _issue_one_time_token(db, user, TokenPurpose.PASSWORD_RESET, timedelta(minutes=get_settings().password_reset_expire_minutes))
    db.commit()
    email_service.send_password_reset_email(user.email, user.full_name, raw_token)


def reset_password(db: Session, raw_token: str, new_password: str) -> User:
    token = _consume_one_time_token(db, raw_token, TokenPurpose.PASSWORD_RESET)
    user = db.get(User, token.user_id)
    if user is None:
        raise InvalidToken()
    user.password_hash = hash_password(new_password)
    user.password_changed_at = utcnow()
    # A reset proves control of the mailbox, so it may as well verify the email.
    if user.status == UserStatus.PENDING_VERIFICATION:
        user.status = UserStatus.ACTIVE
    db.commit()
    return user
