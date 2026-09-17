"""Database setup using SQLAlchemy 2.0.

We use SQLite so there is nothing to install or configure. The whole database is
a single file, clavyx.db, created automatically on first run.
"""
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

# check_same_thread=False lets SQLite work with FastAPI's threaded requests.
engine = create_engine(
    settings.DB_URL,
    connect_args={"check_same_thread": False} if settings.DB_URL.startswith("sqlite") else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class every model inherits from."""


def get_db():
    """FastAPI dependency that hands each request its own database session
    and always closes it afterwards, even if the request errors."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables on startup. Safe to call every time; it is a no-op once the
    tables already exist."""
    from . import models  # noqa: F401  (import so the models register on Base)
    Base.metadata.create_all(bind=engine)
