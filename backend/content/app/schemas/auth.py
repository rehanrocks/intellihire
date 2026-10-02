"""Request and response bodies for the authentication endpoints."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.company import CompanyPublic
from app.schemas.user import UserPublic

# bcrypt only looks at the first 72 bytes of a password; newer bcrypt versions
# refuse longer input outright, so we cap it in validation.
PASSWORD_FIELD = Field(min_length=8, max_length=72, description="8 to 72 characters")


def _normalise_email(value: str) -> str:
    return value.strip().lower()


class RegisterIndividualRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = PASSWORD_FIELD

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return _normalise_email(v)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("full_name must have at least 2 characters")
        return v


class RegisterCompanyRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    industry: str = Field(min_length=2, max_length=100)
    official_email: EmailStr
    admin_full_name: str = Field(min_length=2, max_length=120)
    admin_contact_phone: str | None = Field(default=None, max_length=40)
    password: str = PASSWORD_FIELD

    @field_validator("official_email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return _normalise_email(v)


class RegisterResponse(BaseModel):
    message: str
    user: UserPublic
    company: CompanyPublic | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return _normalise_email(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserPublic
    dashboard: str  # where the frontend should redirect (US-1.4)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class EmailOnlyRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return _normalise_email(v)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = PASSWORD_FIELD
