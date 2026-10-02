"""US-1.1 Register an individual account."""
import pytest
from sqlalchemy import select

from app.database.models import User
from tests.conftest import API

URL = f"{API}/auth/register/individual"
VALID = {"full_name": "Ali Khan", "email": "Ali@Example.com", "password": "Secret123!"}


def test_register_creates_pending_user_and_sends_verification_email(client, outbox):
    response = client.post(URL, json=VALID)

    assert response.status_code == 201, response.text
    user = response.json()["user"]
    assert user["email"] == "ali@example.com"  # normalised to lowercase
    assert user["full_name"] == "Ali Khan"
    assert user["role"] == "candidate"
    assert user["status"] == "pending_verification"
    assert "password" not in user and "password_hash" not in user

    assert len(outbox) == 1
    email = outbox[0]
    assert email.to == "ali@example.com"
    assert "http://frontend.test/verify-email?token=" in email.body
    assert email.meta["token"] in email.body


def test_password_is_stored_as_bcrypt_hash_not_plaintext(client, db):
    client.post(URL, json=VALID)
    user = db.scalar(select(User).where(User.email == "ali@example.com"))
    assert user.password_hash.startswith("$2b$")
    assert user.password_hash != VALID["password"]


def test_duplicate_email_is_rejected(client):
    assert client.post(URL, json=VALID).status_code == 201
    response = client.post(URL, json=VALID)
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_duplicate_email_check_ignores_case_and_spaces(client):
    client.post(URL, json=VALID)
    response = client.post(URL, json={**VALID, "email": "  ALI@example.COM "})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "bad_payload, broken_field",
    [
        ({**VALID, "password": "short"}, "password"),
        ({**VALID, "password": "x" * 73}, "password"),
        ({**VALID, "email": "not-an-email"}, "email"),
        ({**VALID, "full_name": "A"}, "full_name"),
        ({"email": VALID["email"], "password": VALID["password"]}, "full_name"),
    ],
)
def test_invalid_input_is_rejected_with_422(client, bad_payload, broken_field):
    response = client.post(URL, json=bad_payload)
    assert response.status_code == 422
    assert any(broken_field in err["loc"] for err in response.json()["detail"])


def test_cannot_log_in_before_verifying_email(client):
    client.post(URL, json=VALID)
    response = client.post(f"{API}/auth/login", json={"email": VALID["email"], "password": VALID["password"]})
    assert response.status_code == 403
    assert "verify" in response.json()["detail"].lower()
