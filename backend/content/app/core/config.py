"""Application settings.

Backend code must never hard-code secrets or environment-specific values
(database passwords, signing keys, ports). Instead we read them from
environment variables, with a `.env` file as a convenience for local work.
`pydantic-settings` does the reading and type-checks every value.

Usage anywhere in the app:

    from app.core.config import get_settings
    settings = get_settings()
    settings.database_url
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- general ---
    app_name: str = "IntelliHire API"
    environment: str = "development"  # development | test | production
    debug: bool = False
    api_prefix: str = "/api/v1"
    # The frontend address is used to build links that we put inside emails
    # (verify-email link, reset-password link).
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["*"]

    # --- database ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/intellihire"

    # --- security ---
    # Signs every JWT. If it leaks, anyone can forge logins, so it is a secret.
    # HS256 wants at least 32 bytes; generate a real one for production with
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: str = "dev-only-secret-change-me-before-any-real-deployment"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # US-1.4: 24-hour sessions
    email_verification_expire_hours: int = 24   # US-1.2
    password_reset_expire_minutes: int = 60     # US-1.6
    # bcrypt "cost". 12 is a sane production default (~250 ms per hash);
    # tests lower it to 4 so hashing is instant.
    bcrypt_rounds: int = 12

    # --- rate limiting (US-1.4: protect auth endpoints from brute force) ---
    rate_limit_enabled: bool = True
    rate_limit_auth_requests: int = 10
    rate_limit_auth_window_seconds: int = 60

    # --- email ---
    email_backend: str = "console"  # console | memory | smtp
    email_from: str = "IntelliHire <no-reply@intellihire.local>"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # --- file storage (US-1.7: CV upload) ---
    upload_dir: str = "uploads"
    max_cv_size_bytes: int = 5 * 1024 * 1024  # 5 MB


@lru_cache
def get_settings() -> Settings:
    """Build the Settings object once and reuse it (cheap, and consistent)."""
    return Settings()
