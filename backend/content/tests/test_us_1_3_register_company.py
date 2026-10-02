"""US-1.3 Register a company account, US-3.6 approval decision, US-12.4 admin approves/rejects."""
from app.core.permissions import Role
from tests.conftest import API, bearer

REGISTER = f"{API}/auth/register/company"
LOGIN = f"{API}/auth/login"
COMPANY = {
    "company_name": "Nexus Tech",
    "industry": "Technology",
    "official_email": "CEO@NexusTech.com",
    "admin_full_name": "Sara Ahmed",
    "admin_contact_phone": "+92-300-1234567",
    "password": "Company123!",
}


def test_register_company_creates_pending_company_and_admin_user(client, outbox):
    response = client.post(REGISTER, json=COMPANY)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["company"]["name"] == "Nexus Tech"
    assert body["company"]["approval_status"] == "pending"
    assert body["user"]["email"] == "ceo@nexustech.com"
    assert body["user"]["role"] == "company_admin"
    assert body["user"]["company_id"] == body["company"]["id"]
    assert body["user"]["company_approval_status"] == "pending"

    assert len(outbox) == 1
    assert outbox[0].to == "ceo@nexustech.com"
    assert "review" in outbox[0].body.lower()


def test_company_admin_can_log_in_but_company_features_stay_locked(client):
    client.post(REGISTER, json=COMPANY)
    login = client.post(LOGIN, json={"email": COMPANY["official_email"], "password": COMPANY["password"]})
    assert login.status_code == 200
    assert login.json()["dashboard"] == "/company/dashboard"
    token = login.json()["access_token"]

    status = client.get(f"{API}/company/me/status", headers=bearer(token))
    assert status.status_code == 200
    assert status.json()["approval_status"] == "pending"

    locked = client.get(f"{API}/company/me", headers=bearer(token))
    assert locked.status_code == 403
    assert "awaiting approval" in locked.json()["detail"]


def test_official_email_must_be_unique_across_companies_and_users(client, register_candidate):
    assert client.post(REGISTER, json=COMPANY).status_code == 201
    assert client.post(REGISTER, json=COMPANY).status_code == 409

    register_candidate(email="person@example.com")
    clash = client.post(REGISTER, json={**COMPANY, "official_email": "person@example.com"})
    assert clash.status_code == 409
    assert clash.json()["detail"] == "Email already registered"


def test_platform_admin_approval_unlocks_company_features(client, make_user, login, outbox):
    company_id = client.post(REGISTER, json=COMPANY).json()["company"]["id"]
    make_user("admin@intellihire.com", role=Role.PLATFORM_ADMIN)
    admin = bearer(login("admin@intellihire.com"))

    pending = client.get(f"{API}/admin/companies/pending", headers=admin)
    assert [c["id"] for c in pending.json()] == [company_id]

    outbox.clear()
    approved = client.post(f"{API}/admin/companies/{company_id}/approve", headers=admin)
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "approved"
    assert approved.json()["rejection_reason"] is None
    assert outbox[-1].to == "ceo@nexustech.com" and outbox[-1].meta["approved"] is True

    company_admin = bearer(login(COMPANY["official_email"], COMPANY["password"]))
    assert client.get(f"{API}/company/me", headers=company_admin).status_code == 200
    assert client.get(f"{API}/admin/companies/pending", headers=admin).json() == []


def test_platform_admin_rejection_sends_reason(client, make_user, login, outbox):
    company_id = client.post(REGISTER, json=COMPANY).json()["company"]["id"]
    make_user("admin@intellihire.com", role=Role.PLATFORM_ADMIN)
    admin = bearer(login("admin@intellihire.com"))

    outbox.clear()
    rejected = client.post(f"{API}/admin/companies/{company_id}/reject", headers=admin, json={"reason": "Website does not exist"})
    assert rejected.status_code == 200
    assert rejected.json()["approval_status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Website does not exist"
    assert "Website does not exist" in outbox[-1].body

    company_admin = bearer(login(COMPANY["official_email"], COMPANY["password"]))
    assert client.get(f"{API}/company/me", headers=company_admin).status_code == 403


def test_only_platform_admin_can_decide(client, login):
    company_id = client.post(REGISTER, json=COMPANY).json()["company"]["id"]
    company_admin = bearer(login(COMPANY["official_email"], COMPANY["password"]))
    response = client.post(f"{API}/admin/companies/{company_id}/approve", headers=company_admin)
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized Access"
