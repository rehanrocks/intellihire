"""Company-staff endpoints: /company/... (gated by approval, US-1.3 / US-3.6)."""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_approved_company
from app.core.permissions import COMPANY_ROLES
from app.core.exceptions import UnauthorizedAccess
from app.database.models import User
from app.schemas.company import CompanyPublic

router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/me/status", response_model=CompanyPublic, summary="My company and its approval status (works while pending)")
def company_status(user: User = Depends(get_current_user)):
    if user.role not in COMPANY_ROLES or user.company is None:
        raise UnauthorizedAccess()
    return CompanyPublic.model_validate(user.company)


@router.get("/me", response_model=CompanyPublic, summary="My company dashboard data (approved companies only)")
def company_me(user: User = Depends(require_approved_company)):
    return CompanyPublic.model_validate(user.company)
