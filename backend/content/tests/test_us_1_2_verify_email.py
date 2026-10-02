"""US-1.2 Verify my email address (and resend the link)."""
from datetime import timedelta

from sqlalchemy import select

from app.core.time import utcnow
from app.database.models import OneTimeToken
from tests.conftest import API

REGISTER = f"{API}/auth/register/individual"
VERIFY = f"{API}/auth/verify-email"
RESEND = f"{API}/auth/resend-verification"
LOGIN = f"{API}/auth/login"
VALID = {"full_name": "Ali Khan", "email": "ali@example.com", "password": "Secret123!"}


def test_valid_link_activates_account_and_allows_login(client, outbox):
    client.post(REGISTER, json=VALID)
    token = outbox[-1].meta["token"]

    response = client.post(VERIFY, json={"token": token})
    assert response.status_code == 200, response.text

    login = client.post(LOGIN, json={"email": VALID["email"], "password": VALID["password"]})
    assert login.status_code == 200
    assert login.json()["user"]["status"] == "active"
    assert login.json()["dashboard"] == "/candidate/dashboard"


def test_link_can_be_opened_with_a_plain_get(client, outbox):
    client.post(REGISTER, json=VALID)
    token = outbox[-1].meta["token"]
    response = client.get(f"{VERIFY}?token={token}")
    assert response.status_code == 200


def test_link_cannot_be_used_twice(client, outbox):
    client.post(REGISTER, json=VALID)
    token = outbox[-1].meta["token"]
    assert client.post(VERIFY, json={"token": token}).status_code == 200

    response = client.post(VERIFY, json={"token": token})
    assert response.status_code == 400
    assert "already been used" in response.json()["detail"]


def test_garbage_token_is_rejected(client):
    response = client.post(VERIFY, json={"token": "definitely-not-a-real-token"})
    assert response.status_code == 400


def test_expired_link_is_rejected_and_resend_issues_a_working_one(client, outbox, db):
    client.post(REGISTER, json=VALID)
    old_token = outbox[-1].meta["token"]

    # Simulate the 24 hours passing by moving the expiry into the past.
    row = db.scalar(select(OneTimeToken))
    row.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()

    expired = client.post(VERIFY, json={"token": old_token})
    assert expired.status_code == 400
    assert "expired" in expired.json()["detail"].lower()

    resend = client.post(RESEND, json={"email": VALID["email"]})
    assert resend.status_code == 200
    assert len(outbox) == 2
    new_token = outbox[-1].meta["token"]
    assert new_token != old_token

    assert client.post(VERIFY, json={"token": new_token}).status_code == 200
    # The old link stays dead even though it was never "used".
    assert client.post(VERIFY, json={"token": old_token}).status_code == 400


def test_resend_gives_the_same_answer_for_unknown_and_already_active_emails(client, outbox, register_candidate):
    unknown = client.post(RESEND, json={"email": "nobody@example.com"})
    assert unknown.status_code == 200
    assert outbox == []

    register_candidate(email="done@example.com")  # verified during registration helper
    outbox.clear()
    active = client.post(RESEND, json={"email": "done@example.com"})
    assert active.status_code == 200
    assert active.json() == unknown.json()
    assert outbox == []  # nothing sent to an already-active account
