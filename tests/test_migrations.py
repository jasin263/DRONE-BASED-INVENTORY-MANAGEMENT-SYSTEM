"""Opt-in migration round-trip and Gate 0 integrity checks."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MIGRATION_TESTS") != "1",
    reason="set RUN_MIGRATION_TESTS=1 for the destructive migration round-trip",
)


def test_migration_round_trip_and_gate0_constraints() -> None:
    root = Path(__file__).parents[1]
    config = Config(str(root / "backend" / "db" / "alembic.ini"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg://drims:drims_password@postgres:5432/drims"))
    with engine.begin() as connection:
        tables = set(
            connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public'"
                )
            ).scalars()
        )
        assert {"audit_log", "role", "job", "dead_letter", "scan_event"} <= tables
        assert connection.execute(
            text(
                "SELECT 1 FROM pg_constraint WHERE conname='ck_location_data_source'"
            )
        ).scalar_one()
        assert connection.execute(
            text(
                "SELECT 1 FROM pg_trigger WHERE tgname='audit_log_no_update_delete'"
            )
        ).scalar_one()
        assert connection.execute(
            text(
                "SELECT 1 FROM pg_partitioned_table pt "
                "JOIN pg_class c ON c.oid=pt.partrelid "
                "WHERE c.relname='scan_event'"
            )
        ).scalar_one()
