"""Role-based access control (US-1.8).

Two layers:

- Roles: the big buckets a user belongs to (candidate, company admin, ...).
- Permissions: fine-grained actions ("job.delete"). Each role maps to the set
  of actions it may perform. Endpoints ask for a permission, not a role, so
  changing who may do what is a one-line edit here instead of a hunt through
  the codebase.
"""
from enum import Enum


class Role(str, Enum):
    CANDIDATE = "candidate"
    COMPANY_ADMIN = "company_admin"
    HR_MANAGER = "hr_manager"
    RECRUITER = "recruiter"
    VIEWER = "viewer"
    PLATFORM_ADMIN = "platform_admin"


COMPANY_ROLES = {Role.COMPANY_ADMIN, Role.HR_MANAGER, Role.RECRUITER, Role.VIEWER}

# Where the frontend should send a user after login (US-1.4).
DASHBOARD_BY_ROLE = {
    Role.CANDIDATE: "/candidate/dashboard",
    Role.COMPANY_ADMIN: "/company/dashboard",
    Role.HR_MANAGER: "/company/dashboard",
    Role.RECRUITER: "/company/dashboard",
    Role.VIEWER: "/company/dashboard",
    Role.PLATFORM_ADMIN: "/admin/dashboard",
}

_COMPANY_READ = {"company.view", "job.view", "candidate.view", "report.view"}
_COMPANY_WRITE = {"job.create", "job.edit", "job.close", "candidate.decide", "community.manage"}

PERMISSIONS: dict[Role, set[str]] = {
    Role.CANDIDATE: {"profile.manage", "interview.practice", "community.join", "application.track"},
    Role.VIEWER: set(_COMPANY_READ),
    Role.RECRUITER: _COMPANY_READ | {"job.create", "job.edit", "candidate.decide"},
    Role.HR_MANAGER: _COMPANY_READ | _COMPANY_WRITE | {"job.delete"},
    Role.COMPANY_ADMIN: _COMPANY_READ | _COMPANY_WRITE | {"job.delete", "company.manage", "staff.manage"},
    Role.PLATFORM_ADMIN: {"admin.panel", "user.manage", "company.manage.any", "account.suspend", "llm.configure"},
}


def has_permission(role: Role, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())
