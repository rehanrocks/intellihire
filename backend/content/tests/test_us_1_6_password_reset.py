"""US-1.6 Recover a forgotten password."""
import time
from datetime import timedelta

from sqlalchemy import select

from app.core.time import utcnow
from app.database.models import OneTimeToken, TokenPurpose, UserStatus
from tests.conftest import API, bearer

FORGOT = f"{API}/auth/forgot-password"
RESET = f"{API}/auth/reset-password"
LOGIN = f"{API}/auth/login"
ME = f"{API}/users/me"


def test_unknown_email_gets_neutral_answer_and_no_email(client, outbox):
    response = client.post(FORGOT, json={"email": "ghost@example.com"})
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    assert outbox == []


def test_reset_flow_changes_password(client, outbox, register_candidate):
    register_candidate(email="ali@example.com", password="OldPass123!")
    outbox.clear()

    forgot = client.post(FORGOT, json={"email": "ali@example.com"})
    assert forgot.status_code == 200
    assert len(outbox) == 1 and "reset-password?token=" in outbox[0].body
    token = outbox[0].meta["token"]

    reset = client.post(RESET, json={"token": token, "new_password": "NewPass456!"})
    assert reset.status_code == 200, reset.text

    assert client.post(LOGIN, json={"email": "ali@example.com", "password": "OldPass123!"}).status_code == 401
    assert client.post(LOGIN, json={"email": "ali@example.com", "password": "NewPass456!"}).status_code == 200


def test_reset_token_is_single_use(client, outbox, register_candidate):
    register_candidate(email="ali@example.com")
    client.post(FORGOT, json={"email": "ali@example.com"})
    token = outbox[-1].meta["token"]
    assert client.post(RESET, json={"token": token, "new_password": "NewPass456!"}).status_code == 200
    again = client.post(RESET, json={"token": token, "new_password": "Other789!!"})
    assert again.status_code == 400


def test_reset_logs_out_existing_sessions(client, outbox, register_candidate, login):
    register_candidate(email="ali@example.com")
    old_session = bearer(login("ali@example.com"))
    assert client.get(ME, headers=old_session).status_code == 200

    # JWT issue times are whole seconds; make sure the reset lands in a later
    # second than the old login, as it always would for a real user.
    time.sleep(1.1)
    client.post(FORGOT, json={"email": "ali@example.com"})
    client.post(RESET, json={"token": outbox[-1].meta["token"], "new_password": "NewPass456!"})

    assert client.get(ME, headers=old_session).status_code == 401
    assert client.get(ME, headers=bearer(login("ali@example.com", "NewPass456!"))).status_code == 200


def test_expired_reset_token_is_rejected(client, outbox, register_candidate, db):
    register_candidate(email="ali@example.com")
    client.post(FORGOT, json={"email": "ali@example.com"})
    row = db.scalar(select(OneTimeToken).where(OneTimeToken.purpose == TokenPurpose.PASSWORD_RESET))
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    response = client.post(RESET, json={"token": outbox[-1].meta["token"], "new_password": "NewPass456!"})
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


def test_weak_new_password_is_rejected(client, outbox, register_candidate):
    register_candidate(email="ali@example.com")
    client.post(FORGOT, json={"email": "ali@example.com"})
    response = client.post(RESET, json={"token": outbox[-1].meta["token"], "new_password": "short"})
    assert response.status_code == 422


def test_suspended_accounts_receive_no_reset_email(client, outbox, make_user):
    make_user("banned@example.com", status=UserStatus.SUSPENDED)
    assert client.post(FORGOT, json={"email": "banned@example.com"}).status_code == 200
    assert outbox == []
