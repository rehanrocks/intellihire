"""Platform-administrator endpoints: /admin/... (US-1.8 RBAC, US-12.4 company approval)."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.core.permissions import Role
from app.database.models import Company, CompanyApprovalStatus, User
from app.database.session import get_db
from app.schemas.company import CompanyDecisionRequest, CompanyPublic
from app.services import auth_service

router = APIRouter(prefix="/admin", tags=["Platform Admin"], dependencies=[Depends(require_roles(Role.PLATFORM_ADMIN))])


class AdminOverview(BaseModel):
    total_users: int
    total_companies: int
    pending_companies: int


@router.get("/overview", response_model=AdminOverview, summary="Counts for the admin dashboard")
def overview(db: Session = Depends(get_db)):
    return AdminOverview(
        total_users=db.scalar(select(func.count()).select_from(User)) or 0,
        total_companies=db.scalar(select(func.count()).select_from(Company)) or 0,
        pending_companies=db.scalar(select(func.count()).select_from(Company).where(Company.approval_status == CompanyApprovalStatus.PENDING)) or 0,
    )


@router.get("/companies/pending", response_model=list[CompanyPublic], summary="US-12.4 Companies awaiting approval")
def pending_companies(db: Session = Depends(get_db)):
    return [CompanyPublic.model_validate(c) for c in db.scalars(select(Company).where(Company.approval_status == CompanyApprovalStatus.PENDING).order_by(Company.created_at))]


@router.post("/companies/{company_id}/approve", response_model=CompanyPublic, summary="US-12.4 Approve a company")
def approve_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return CompanyPublic.model_validate(auth_service.decide_company(db, company_id, approve=True, reason=None))


@router.post("/companies/{company_id}/reject", response_model=CompanyPublic, summary="US-12.4 Reject a company with a reason")
def reject_company(company_id: uuid.UUID, body: CompanyDecisionRequest, db: Session = Depends(get_db)):
    return CompanyPublic.model_validate(auth_service.decide_company(db, company_id, approve=False, reason=body.reason))
