"""Database connection plumbing.

Vocabulary:
- Engine:  knows how to talk to one database URL and keeps a pool of
           reusable connections.
- Session: a short-lived "unit of work". A request opens one, reads/writes
           through it, commits (or rolls back), and closes it.
- Base:    the parent class of every ORM model; it collects table metadata
           so Alembic can diff it against the real database.
"""
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str, **kwargs) -> Engine:
    if database_url.startswith("sqlite"):
        # SQLite is single-threaded by default; FastAPI serves requests from a
        # thread pool, so we relax that check. We also switch on foreign keys,
        # which SQLite leaves off unless asked.
        kwargs.setdefault("connect_args", {"check_same_thread": False})
        engine = create_engine(database_url, **kwargs)

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        return engine
    # pool_pre_ping: test a pooled connection before using it, so a database
    # restart does not surface as a random 500 later.
    return create_engine(database_url, pool_pre_ping=True, **kwargs)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one Session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
