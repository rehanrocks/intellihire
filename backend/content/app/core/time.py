"""One place that decides what "now" means.

Rule for this project: every datetime we store is naive UTC (no timezone
attached, but always meaning UTC). That keeps SQLite (tests) and PostgreSQL
(production) behaving identically and avoids the classic
"can't compare offset-naive and offset-aware datetimes" bug.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def from_timestamp(seconds: float | int) -> datetime:
    """Unix timestamp (as found in JWT `iat`/`exp` claims) -> naive UTC datetime."""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
