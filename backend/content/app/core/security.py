"""Security primitives: password hashing, JWT sessions, one-time tokens.

Two ideas every backend engineer must know:

1. HASHING is one-way. We never store a password, only its bcrypt hash.
   To check a login we hash the typed password and compare hashes.
   bcrypt is deliberately slow and salted, which defeats brute force
   and rainbow tables.

2. A JWT (JSON Web Token) is a signed statement such as
   {"sub": "<user id>", "role": "candidate", "exp": <time>}.
   The server signs it with SECRET_KEY. Anyone can read it, nobody can alter
   it without the key. The client sends it back on every request in the
   `Authorization: Bearer <token>` header, which is how we know who is calling
   without a server-side session store.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


# ----------------------------------------------------------------------------
# Passwords
# ----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash in the database: treat as "does not match".
        return False


# ----------------------------------------------------------------------------
# JWT access tokens (login sessions)
# ----------------------------------------------------------------------------
def create_access_token(*, user_id: uuid.UUID, role: str, expires_minutes: int | None = None) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at).

    `jti` is a unique id for this token. Storing it lets us revoke a token on
    logout (US-1.5) even though JWTs are otherwise stateless.
    """
    settings = get_settings()
    minutes = settings.access_token_expire_minutes if expires_minutes is None else expires_minutes
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=minutes)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at.replace(tzinfo=None)


def decode_access_token(token: str) -> dict:
    """Validate signature and expiry. Raises jwt.PyJWTError on any problem."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


# ----------------------------------------------------------------------------
# One-time tokens (email verification, password reset)
# ----------------------------------------------------------------------------
def generate_one_time_token() -> str:
    """A long random string that is emailed to the user.

    We store only its SHA-256 hash in the database, so a leaked database
    does not let an attacker reuse pending verification/reset links.
    """
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
