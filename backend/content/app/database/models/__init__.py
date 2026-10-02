"""Import every model here so `Base.metadata` knows all tables.

Alembic (migrations) and `Base.metadata.create_all` (tests) both look at
Base.metadata; a model that is never imported is invisible to them.
"""
from app.database.models.company import Company, CompanyApprovalStatus
from app.database.models.profile import CandidateProfile
from app.database.models.token import OneTimeToken, RevokedToken, TokenPurpose
from app.database.models.user import User, UserStatus

__all__ = [
    "Company",
    "CompanyApprovalStatus",
    "CandidateProfile",
    "OneTimeToken",
    "RevokedToken",
    "TokenPurpose",
    "User",
    "UserStatus",
]
