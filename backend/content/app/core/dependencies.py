"""Shared FastAPI dependencies for authentication and authorization.

A *dependency* is a function FastAPI runs before your endpoint and whose
return value is injected as a parameter. Declaring

    def endpoint(user: User = Depends(get_current_user)):

means "this endpoint needs a logged-in user; figure that out for me, or stop
the request with the right error". The endpoint body never sees a request
that failed the check, so security is enforced in one place.
"""
import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AccountSuspended, CompanyNotApproved, NotAuthenticated, UnauthorizedAccess
from app.core.permissions import COMPANY_ROLES, Role, has_permission
from app.core.security import decode_access_token
from app.core.time import from_timestamp
from app.database.models import CompanyApprovalStatus, RevokedToken, User, UserStatus
from app.database.session import get_db

# auto_error=False: we raise our own, consistently worded error instead of
# FastAPI's default when the header is missing.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise NotAuthenticated()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise NotAuthenticated("Session expired. Please log in again.")
    except jwt.PyJWTError:
        raise NotAuthenticated("Invalid authentication token")

    jti = payload.get("jti")
    if jti and db.get(RevokedToken, jti) is not None:
        raise NotAuthenticated("Session has been logged out. Please log in again.")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise NotAuthenticated("Invalid authentication token")

    user = db.get(User, user_id)
    if user is None:
        raise NotAuthenticated("Invalid authentication token")

    # Tokens issued before the last password change are no longer trusted.
    # JWT `iat` has whole-second precision, so compare at that precision too;
    # otherwise a token minted in the same second as the change would be rejected.
    if user.password_changed_at is not None:
        issued_at = from_timestamp(payload.get("iat", 0))
        if issued_at < user.password_changed_at.replace(microsecond=0):
            raise NotAuthenticated("Session expired. Please log in again.")

    if user.status == UserStatus.SUSPENDED:
        raise AccountSuspended()

    return user


def require_roles(*roles: Role):
    """Only let the listed roles through (US-1.8)."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise UnauthorizedAccess()
        return user

    return dependency


def require_permission(permission: str):
    """Only let roles that hold `permission` through (US-1.8)."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise UnauthorizedAccess()
        return user

    return dependency


def require_approved_company(user: User = Depends(get_current_user)) -> User:
    """Company staff may use company features only after admin approval (US-1.3, US-3.6)."""
    if user.role not in COMPANY_ROLES:
        raise UnauthorizedAccess()
    if user.company is None or user.company.approval_status != CompanyApprovalStatus.APPROVED:
        raise CompanyNotApproved()
    return user
