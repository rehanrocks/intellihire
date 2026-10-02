"""US-1.7 Manage my profile and CV."""
import os

from app.core.config import get_settings
from app.core.permissions import Role
from tests.conftest import API, bearer

PROFILE = f"{API}/users/me/profile"
CV = f"{API}/users/me/cv"
ME = f"{API}/users/me"

PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def test_profile_starts_empty_with_completion_indicator(client, auth_headers):
    response = client.get(PROFILE, headers=auth_headers())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Ali Khan"
    assert body["skills"] == [] and body["education"] == [] and body["cv"] is None
    assert body["completion_percent"] == 11  # 1 of 9 pieces (full name) present
    assert "cv" in body["missing_fields"] and "skills" in body["missing_fields"]


def test_partial_update_saves_only_sent_fields(client, auth_headers):
    headers = auth_headers()
    first = client.put(PROFILE, headers=headers, json={"job_title": "Frontend Developer", "skills": ["React", "React", " TypeScript "]})
    assert first.status_code == 200, first.text
    assert first.json()["job_title"] == "Frontend Developer"
    assert first.json()["skills"] == ["React", "TypeScript"]  # trimmed and de-duplicated

    second = client.put(
        PROFILE,
        headers=headers,
        json={
            "full_name": "Ali Hassan",
            "location": "Lahore, Pakistan",
            "education": [{"degree": "BS Software Engineering", "institution": "COMSATS Lahore", "year": 2027}],
            "experience": [{"company": "Acme", "role": "Intern", "start_date": "2025-06", "end_date": None, "description": "Built dashboards"}],
        },
    )
    body = second.json()
    assert body["job_title"] == "Frontend Developer"  # untouched by the second update
    assert body["education"][0]["institution"] == "COMSATS Lahore"
    assert body["experience"][0]["end_date"] is None
    assert body["completion_percent"] == 67  # 6 of 9
    assert client.get(ME, headers=headers).json()["full_name"] == "Ali Hassan"


def test_linkedin_url_must_be_a_web_address(client, auth_headers):
    response = client.put(PROFILE, headers=auth_headers(), json={"linkedin_url": "linkedin.com/in/ali"})
    assert response.status_code == 422


def test_company_staff_cannot_use_candidate_profile(client, make_user, login):
    make_user("hr@nexus.com", role=Role.HR_MANAGER)
    response = client.get(PROFILE, headers=bearer(login("hr@nexus.com")))
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized Access"


def test_cv_upload_download_and_delete(client, auth_headers):
    headers = auth_headers()

    upload = client.post(CV, headers=headers, files={"file": ("Ali-CV.pdf", PDF_BYTES, "application/pdf")})
    assert upload.status_code == 200, upload.text
    assert upload.json()["cv"]["original_name"] == "Ali-CV.pdf"
    assert "cv" not in upload.json()["missing_fields"]

    download = client.get(CV, headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.content == PDF_BYTES

    deleted = client.delete(CV, headers=headers)
    assert deleted.status_code == 200 and deleted.json()["cv"] is None
    assert client.get(CV, headers=headers).status_code == 404


def test_replacing_cv_removes_the_old_file(client, auth_headers):
    headers = auth_headers()
    client.post(CV, headers=headers, files={"file": ("v1.pdf", PDF_BYTES, "application/pdf")})
    client.post(CV, headers=headers, files={"file": ("v2.pdf", PDF_BYTES + b"v2", "application/pdf")})

    user_id = client.get(ME, headers=headers).json()["id"]
    folder = os.path.join(get_settings().upload_dir, "cvs", user_id)
    assert len(os.listdir(folder)) == 1
    assert client.get(CV, headers=headers).content.endswith(b"v2")


def test_non_pdf_uploads_are_rejected(client, auth_headers):
    headers = auth_headers()
    jpg = client.post(CV, headers=headers, files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0 jpeg", "image/jpeg")})
    assert jpg.status_code == 400 and jpg.json()["detail"] == "Only PDF files are accepted"

    fake = client.post(CV, headers=headers, files={"file": ("cv.pdf", b"this is a text file", "application/pdf")})
    assert fake.status_code == 400 and "not a valid PDF" in fake.json()["detail"]


def test_cv_over_5mb_is_rejected(client, auth_headers):
    too_big = b"%PDF-1.4" + b"0" * (5 * 1024 * 1024)
    response = client.post(CV, headers=auth_headers(), files={"file": ("big.pdf", too_big, "application/pdf")})
    assert response.status_code == 413
