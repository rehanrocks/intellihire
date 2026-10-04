"""Database connection and session management.

Uses environment variables for configuration. Provides a FastAPI dependency
`get_db` that yields a SQLAlchemy session per request.
"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool


def _get_database_url() -> str:
    """Build the SQLAlchemy database URL from environment variables.

    Expected variables (with defaults for local dev):
    - POSTGRES_USER (default: postgres)
    - POSTGRES_PASSWORD (default: postgres)
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: intellihire)

    Alternatively, set DATABASE_URL directly to override everything.
    """
    # Allow full override via DATABASE_URL (e.g. for managed DBs or SQLite tests)
    if url := os.getenv("DATABASE_URL"):
        return url

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "intellihire")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


# ---------------------------------------------------------------------------
# Engine & SessionFactory (module-level singletons)
# ---------------------------------------------------------------------------
# Use NullPool for serverless / test environments; otherwise default pool is fine.
_engine = create_engine(
    _get_database_url(),
)

_SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a request-scoped SQLAlchemy session.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...

    The session is committed if the request succeeds, rolled back on exception,
    and always closed.
    """
    db = _SessionFactory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
