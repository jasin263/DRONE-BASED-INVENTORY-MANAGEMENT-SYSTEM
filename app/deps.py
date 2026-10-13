"""Dependency injection for DIMS application."""

from typing import Generator
from sqlalchemy.orm import Session

from .core.db import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """Get a database session yield dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()