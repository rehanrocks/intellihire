"""NFR-03 brute-force protection and the health endpoint."""
from app.core import rate_limit as rl
from app.core.config import get_settings
from tests.conftest import API

LOGIN = f"{API}/auth/login"


def test_limiter_allows_up_to_the_limit_then_blocks_until_the_window_passes():
    limiter = rl.RateLimiter(max_requests=3, window_seconds=60)
    assert [limiter.allow("ip", now=0.0) for _ in range(3)] == [True, True, True]
    assert limiter.allow("ip", now=1.0) is False
    assert limiter.allow("other-ip", now=1.0) is True  # keys are independent
    assert limiter.allow("ip", now=61.0) is True  # window slid past the first hits


def test_login_endpoint_returns_429_after_too_many_attempts(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_auth_requests", 3)
    rl._limiters.clear()
    try:
        payload = {"email": "ghost@example.com", "password": "wrong-password"}
        for _ in range(3):
            assert client.post(LOGIN, json=payload).status_code == 401
        blocked = client.post(LOGIN, json=payload)
        assert blocked.status_code == 429
        assert "Too many requests" in blocked.json()["detail"]
    finally:
        rl._limiters.clear()


def test_health_and_docs_are_served(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
