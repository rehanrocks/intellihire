"""Shared test setup (pytest loads this file automatically).

How the tests work:
- Settings are forced to test values BEFORE the app is imported (settings are
  read once and cached). Emails go to an in-memory outbox, rate limiting is
  off, bcrypt is fast, uploads go to a temp folder.
- Every test gets a brand-new SQLite database file, so tests cannot leak state
  into each other.
- `client` is FastAPI's TestClient: it calls the app in-process, no server needed.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="intellihire-tests-")
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite://",  # placeholder; get_db is overridden per test below
        "SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes-long",
        "EMAIL_BACKEND": "memory",
        "RATE_LIMIT_ENABLED": "false",
        "BCRYPT_ROUNDS": "4",
        "UPLOAD_DIR": os.path.join(_TMP, "uploads"),
        "FRONTEND_URL": "http://frontend.test",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.permissions import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.models import User, UserStatus  # noqa: E402
from app.database.session import Base, get_db, make_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.email_service import get_email_backend  # noqa: E402

API = "/api/v1"


@pytest.fixture()
def engine(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory):
    """A session the *test itself* can use to inspect or tweak the database."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def outbox():
    backend = get_email_backend()
    backend.clear()
    return backend.outbox


# ----------------------------------------------------------------------------
# Helpers that tests call to set up state quickly
# ----------------------------------------------------------------------------
@pytest.fixture()
def make_user(db):
    def _make(email, password="Secret123!", role=Role.CANDIDATE, status=UserStatus.ACTIVE, full_name="Test User", company_id=None):
        user = User(email=email.lower(), full_name=full_name, password_hash=hash_password(password), role=role, status=status, company_id=company_id)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def register_candidate(client, outbox):
    def _register(email="ali@example.com", password="Secret123!", full_name="Ali Khan", verify=True):
        response = client.post(f"{API}/auth/register/individual", json={"full_name": full_name, "email": email, "password": password})
        assert response.status_code == 201, response.text
        if verify:
            token = outbox[-1].meta["token"]
            verified = client.post(f"{API}/auth/verify-email", json={"token": token})
            assert verified.status_code == 200, verified.text
        return response.json()["user"]

    return _register


@pytest.fixture()
def login(client):
    def _login(email, password="Secret123!"):
        response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login


@pytest.fixture()
def auth_headers(register_candidate, login):
    """Register + verify + log in a candidate; return the Authorization header."""

    def _headers(email="ali@example.com", password="Secret123!"):
        register_candidate(email=email, password=password)
        return {"Authorization": f"Bearer {login(email, password)}"}

    return _headers


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
