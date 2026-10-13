"""Alembic model metadata.

The application ORM is the single source of truth for table metadata.  Keeping
this module as a small compatibility layer prevents Alembic and workers from
loading a second, incomplete model definition.
"""

from app.models import Base

__all__ = ["Base"]

