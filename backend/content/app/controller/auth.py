"""Authentication endpoints: /auth/...

Each function here is deliberately small. It receives an already-validated
body (a schema), hands it to the service, and shapes the reply. If you find
yourself writing business rules in a controller, move them to a service.
"""
from fastapi import APIRouter, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.dependencies import bearer_scheme, get_current_user
from app.core.rate_limit import rate_limit
from app.core.security import decode_access_token
from app.database.models import User
from app.database.session import get_db
from app.schemas.auth import (
    EmailOnlyRequest,
    LoginRequest,
    RegisterCompanyRequest,
    RegisterIndividualRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.company import CompanyPublic
from app.schemas.user import UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

NEUTRAL_RESET_MESSAGE = "If an account exists for that email, we have sent instructions to it."
NEUTRAL_RESEND_MESSAGE = "If that email is registered and still unverified, a new verification link is on its way."


@router.post("/register/individual", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit("register"))], summary="US-1.1 Register an individual account")
def register_individual(body: RegisterIndividualRequest, db: Session = Depends(get_db)):
    user = auth_service.register_individual(db, body)
    return RegisterResponse(message="Account created. Check your inbox for the verification link.", user=UserPublic.from_user(user))


@router.post("/register/company", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit("register"))], summary="US-1.3 Register a company account")
def register_company(body: RegisterCompanyRequest, db: Session = Depends(get_db)):
    company, admin = auth_service.register_company(db, body)
    return RegisterResponse(
        message="Company registered. A platform administrator will review it; we will email you the decision.",
        user=UserPublic.from_user(admin),
        company=CompanyPublic.model_validate(company),
    )


@router.post("/verify-email", response_model=MessageResponse, summary="US-1.2 Verify email with the emailed token")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    auth_service.verify_email(db, body.token)
    return MessageResponse(message="Email verified. You can now log in.")


@router.get("/verify-email", response_model=MessageResponse, include_in_schema=False)
def verify_email_via_link(token: str = Query(min_length=10, max_length=200), db: Session = Depends(get_db)):
    """Same as POST, for clicking the link directly without a frontend."""
    auth_service.verify_email(db, token)
    return MessageResponse(message="Email verified. You can now log in.")


@router.post("/resend-verification", response_model=MessageResponse, dependencies=[Depends(rate_limit("resend"))],
             summary="US-1.2 Resend the verification link")
def resend_verification(body: EmailOnlyRequest, db: Session = Depends(get_db)):
    auth_service.resend_verification(db, body.email)
    return MessageResponse(message=NEUTRAL_RESEND_MESSAGE)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("login"))], summary="US-1.4 Log in")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    token, expires_at, user, dashboard = auth_service.login(db, body.email, body.password)
    return TokenResponse(access_token=token, expires_at=expires_at, user=UserPublic.from_user(user), dashboard=dashboard)


@router.post("/logout", response_model=MessageResponse, summary="US-1.5 Log out (revoke this token)")
def logout(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    # get_current_user already proved the token is valid, so decoding again cannot fail.
    payload = decode_access_token(credentials.credentials)
    auth_service.logout(db, user, payload)
    return MessageResponse(message="Logged out.")


@router.post("/forgot-password", response_model=MessageResponse, dependencies=[Depends(rate_limit("forgot"))],
             summary="US-1.6 Request a password reset link")
def forgot_password(body: EmailOnlyRequest, db: Session = Depends(get_db)):
    auth_service.request_password_reset(db, body.email)
    return MessageResponse(message=NEUTRAL_RESET_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse, dependencies=[Depends(rate_limit("reset"))],
             summary="US-1.6 Set a new password with the emailed token")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, body.token, body.new_password)
    return MessageResponse(message="Password updated. Please log in with your new password.")
