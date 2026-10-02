"""US-1.8 Role-based access control."""
import pytest
from fastapi import Depends

from app.core.dependencies import require_permission
from app.core.permissions import Role, has_permission
from app.database.models import UserStatus
from app.main import app
from tests.conftest import API, bearer

OVERVIEW = f"{API}/admin/overview"
ME = f"{API}/users/me"


def test_candidate_is_blocked_from_admin_panel(client, auth_headers):
    response = client.get(OVERVIEW, headers=auth_headers())
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized Access"


def test_company_admin_is_blocked_from_admin_panel(client, make_user, login):
    make_user("boss@nexus.com", role=Role.COMPANY_ADMIN)
    assert client.get(OVERVIEW, headers=bearer(login("boss@nexus.com"))).status_code == 403


def test_platform_admin_sees_overview(client, make_user, login, register_candidate):
    register_candidate(email="ali@example.com")
    make_user("admin@intellihire.com", role=Role.PLATFORM_ADMIN)
    response = client.get(OVERVIEW, headers=bearer(login("admin@intellihire.com")))
    assert response.status_code == 200
    assert response.json() == {"total_users": 2, "total_companies": 0, "pending_companies": 0}


@pytest.mark.parametrize(
    "role, permission, allowed",
    [
        (Role.VIEWER, "job.delete", False),
        (Role.VIEWER, "job.view", True),
        (Role.RECRUITER, "job.delete", False),
        (Role.HR_MANAGER, "job.delete", True),
        (Role.COMPANY_ADMIN, "staff.manage", True),
        (Role.HR_MANAGER, "staff.manage", False),
        (Role.CANDIDATE, "job.view", False),
        (Role.PLATFORM_ADMIN, "account.suspend", True),
    ],
)
def test_permission_matrix(role, permission, allowed):
    assert has_permission(role, permission) is allowed


# A throw-away endpoint so we can prove require_permission works end to end
# before the real job endpoints exist (Module 4).
_PROBE = f"{API}/_test/jobs/1"
if not any(getattr(r, "path", None) == _PROBE for r in app.routes):

    @app.delete(_PROBE, dependencies=[Depends(require_permission("job.delete"))], include_in_schema=False)
    def _delete_job_probe():
        return {"deleted": True}


def test_require_permission_lets_hr_manager_but_not_viewer_delete_a_job(client, make_user, login):
    make_user("viewer@nexus.com", role=Role.VIEWER)
    make_user("hr@nexus.com", role=Role.HR_MANAGER)

    assert client.delete(_PROBE, headers=bearer(login("viewer@nexus.com"))).status_code == 403
    assert client.delete(_PROBE, headers=bearer(login("hr@nexus.com"))).status_code == 200


def test_suspending_a_user_kills_their_live_session(client, make_user, login, db):
    user = make_user("ali@example.com")
    headers = bearer(login("ali@example.com"))
    assert client.get(ME, headers=headers).status_code == 200

    user.status = UserStatus.SUSPENDED
    db.commit()

    response = client.get(ME, headers=headers)
    assert response.status_code == 403
    assert "suspended" in response.json()["detail"].lower()
