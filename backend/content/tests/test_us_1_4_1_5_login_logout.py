"""US-1.4 Log in and US-1.5 Log out."""
from datetime import datetime, timedelta

import jwt
import pytest

from app.core.permissions import Role
from app.core.security import create_access_token
from app.core.time import utcnow
from app.database.models import UserStatus
from tests.conftest import API, bearer

LOGIN = f"{API}/auth/login"
LOGOUT = f"{API}/auth/logout"
ME = f"{API}/users/me"


def test_wrong_password_and_unknown_email_give_the_same_message(client, register_candidate):
    register_candidate(email="ali@example.com", password="Secret123!")

    wrong = client.post(LOGIN, json={"email": "ali@example.com", "password": "nope-nope"})
    unknown = client.post(LOGIN, json={"email": "ghost@example.com", "password": "Secret123!"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Invalid email or password"


def test_suspended_account_cannot_log_in(client, make_user):
    make_user("banned@example.com", status=UserStatus.SUSPENDED)
    response = client.post(LOGIN, json={"email": "banned@example.com", "password": "Secret123!"})
    assert response.status_code == 403
    assert "suspended" in response.json()["detail"].lower()


def test_successful_login_returns_24h_token_user_and_dashboard(client, register_candidate, db):
    register_candidate(email="ali@example.com")
    response = client.post(LOGIN, json={"email": "ALI@example.com", "password": "Secret123!"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "ali@example.com"
    assert body["dashboard"] == "/candidate/dashboard"

    expires_at = datetime.fromisoformat(body["expires_at"])
    assert timedelta(hours=23, minutes=59) < expires_at - utcnow() <= timedelta(hours=24)

    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["role"] == "candidate" and claims["sub"] == body["user"]["id"] and "jti" in claims


@pytest.mark.parametrize(
    "role, dashboard",
    [
        (Role.CANDIDATE, "/candidate/dashboard"),
        (Role.HR_MANAGER, "/company/dashboard"),
        (Role.RECRUITER, "/company/dashboard"),
        (Role.PLATFORM_ADMIN, "/admin/dashboard"),
    ],
)
def test_login_redirects_each_role_to_its_dashboard(client, make_user, role, dashboard):
    make_user("someone@example.com", role=role)
    response = client.post(LOGIN, json={"email": "someone@example.com", "password": "Secret123!"})
    assert response.json()["dashboard"] == dashboard


def test_login_records_last_login_time(client, make_user, db):
    user = make_user("ali@example.com")
    assert user.last_login_at is None
    client.post(LOGIN, json={"email": "ali@example.com", "password": "Secret123!"})
    db.refresh(user)
    assert user.last_login_at is not None


def test_protected_route_requires_a_valid_token(client, auth_headers):
    assert client.get(ME).status_code == 401
    assert client.get(ME).json()["detail"] == "Not authenticated"
    assert client.get(ME, headers=bearer("this.is.garbage")).status_code == 401

    me = client.get(ME, headers=auth_headers())
    assert me.status_code == 200
    assert me.json()["email"] == "ali@example.com"


def test_expired_token_is_rejected(client, make_user):
    user = make_user("ali@example.com")
    token, _, _ = create_access_token(user_id=user.id, role="candidate", expires_minutes=-1)
    response = client.get(ME, headers=bearer(token))
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_token_signed_with_another_key_is_rejected(client, make_user):
    user = make_user("ali@example.com")
    forged = jwt.encode(
        {"sub": str(user.id), "role": "platform_admin", "jti": "x", "exp": utcnow() + timedelta(hours=1)},
        "attacker-key-that-is-also-long-enough-for-hs256",
        algorithm="HS256",
    )
    assert client.get(ME, headers=bearer(forged)).status_code == 401


def test_logout_revokes_the_token(client, auth_headers):
    headers = auth_headers()
    assert client.get(ME, headers=headers).status_code == 200

    assert client.post(LOGOUT, headers=headers).status_code == 200

    after = client.get(ME, headers=headers)
    assert after.status_code == 401
    assert "logged out" in after.json()["detail"].lower()
    assert client.post(LOGOUT, headers=headers).status_code == 401  # cannot log out twice


def test_logout_only_affects_that_session(client, register_candidate, login):
    register_candidate(email="ali@example.com")
    first, second = bearer(login("ali@example.com")), bearer(login("ali@example.com"))
    client.post(LOGOUT, headers=first)
    assert client.get(ME, headers=first).status_code == 401
    assert client.get(ME, headers=second).status_code == 200
