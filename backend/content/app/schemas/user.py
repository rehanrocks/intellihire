"""User and profile schemas (US-1.1, US-1.4, US-1.7)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.permissions import Role
from app.database.models import CompanyApprovalStatus, User, UserStatus


class UserPublic(BaseModel):
    """What the API says about a user. Note: no password_hash field, ever."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    status: UserStatus
    company_id: uuid.UUID | None = None
    company_approval_status: CompanyApprovalStatus | None = None
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserPublic":
        data = cls.model_validate(user)
        if user.company is not None:
            data.company_approval_status = user.company.approval_status
        return data


# --- profile -----------------------------------------------------------------
class EducationItem(BaseModel):
    degree: str = Field(min_length=1, max_length=120)
    institution: str = Field(min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=1950, le=2100)


class ExperienceItem(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=120)
    start_date: str = Field(min_length=4, max_length=20, description="e.g. 2023-06")
    end_date: str | None = Field(default=None, max_length=20, description="null means current")
    description: str | None = Field(default=None, max_length=2000)


class ProfileUpdate(BaseModel):
    """PUT body. Every field optional: send only what changed."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    linkedin_url: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    education: list[EducationItem] | None = None
    experience: list[ExperienceItem] | None = None
    skills: list[str] | None = Field(default=None, max_length=50)

    @field_validator("linkedin_url")
    @classmethod
    def _must_be_http(cls, value: str | None) -> str | None:
        if value and not value.lower().startswith(("http://", "https://")):
            raise ValueError("linkedin_url must start with http:// or https://")
        return value

    @field_validator("skills")
    @classmethod
    def _clean_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [s.strip() for s in value if s and s.strip()]
        # de-duplicate while keeping order
        return list(dict.fromkeys(cleaned))


class CVInfo(BaseModel):
    original_name: str
    uploaded_at: datetime


class ProfileResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: EmailStr
    job_title: str | None
    location: str | None
    linkedin_url: str | None
    bio: str | None
    education: list[EducationItem]
    experience: list[ExperienceItem]
    skills: list[str]
    cv: CVInfo | None
    completion_percent: int
    missing_fields: list[str]
