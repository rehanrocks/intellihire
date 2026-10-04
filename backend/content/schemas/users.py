"""Pydantic schemas for UserProfile."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileBase(BaseModel):
    """Shared fields for create / update / response."""
    user_type: str = Field(..., max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    tenant_profile_id: Optional[int] = None


class UserProfileCreate(UserProfileBase):
    """Payload for POST /user-profiles."""
    pass


class UserProfileUpdate(BaseModel):
    """Payload for PATCH /user-profiles/{id}. All fields optional."""
    user_type: Optional[str] = Field(default=None, max_length=50)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    tenant_profile_id: Optional[int] = None


class UserProfileRead(UserProfileBase):
    """Response for GET /user-profiles/{id} and list endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None