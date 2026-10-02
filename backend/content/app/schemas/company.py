import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.database.models import CompanyApprovalStatus


class CompanyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str
    official_email: EmailStr
    admin_contact_name: str
    admin_contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    headquarters: str | None = None
    size: str | None = None
    approval_status: CompanyApprovalStatus
    rejection_reason: str | None = None
    created_at: datetime


class CompanyDecisionRequest(BaseModel):
    reason: str | None = None
