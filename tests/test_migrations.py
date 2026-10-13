"""Opt-in migration round-trip and Gate 0 integrity checks."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_migration_round_trip_and_gate0_constraints() -> None:
    root = Path(__file__).parents[1]
    config = Config(str(root / "backend" / "db" / "alembic.ini"))
    database_url = os.getenv(
        "MIGRATION_TEST_DATABASE_URL",
        "postgresql+psycopg://drims:drims_password@postgres:5432/drims_test",
    )
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url

    engine = create_engine(
        database_url
    )
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
