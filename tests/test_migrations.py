"""Isolated migration round-trip and Gate 0 integrity checks."""

import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app import worker_app


def require_test_database(connection) -> None:
    database_name = connection.execute(text("SELECT current_database()")).scalar_one()
    if not database_name.endswith("_test"):
        raise RuntimeError(
            f"Refusing destructive migration test against database {database_name!r}; "
            "database name must end with '_test'."
        )


@pytest.fixture
def migration_test_database():
    database_url = os.environ["MIGRATION_TEST_DATABASE_URL"]
    engine = create_engine(database_url)
    with engine.connect() as connection:
        require_test_database(connection)
    yield database_url
    engine.dispose()


def test_migration_database_guard_rejects_dev_database() -> None:
    class DevConnection:
        def execute(self, statement):
            return type("Result", (), {"scalar_one": lambda self: "drims"})()

    with pytest.raises(RuntimeError, match="drims"):
        require_test_database(DevConnection())


def test_migration_round_trip_and_gate0_constraints(migration_test_database: str) -> None:
    root = Path(__file__).parents[1]
    config = Config(str(root / "backend" / "db" / "alembic.ini"))
    database_url = migration_test_database
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        with create_engine(database_url).connect() as connection:
            require_test_database(connection)
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


def test_partition_maintenance_drains_default_partition(
    migration_test_database: str,
) -> None:
    engine = create_engine(migration_test_database)
    mission_id = f"partition-proof-{uuid.uuid4()}"
    with engine.begin() as connection:
        site_id = connection.execute(
            text(
                "INSERT INTO site (name, code) VALUES (:name, :code) RETURNING id"
            ),
            {"name": mission_id, "code": mission_id[:20]},
        ).scalar_one()
        mission_pk = connection.execute(
            text(
                "INSERT INTO mission (mission_id, site_id, status) "
                "VALUES (:mission_id, :site_id, 'RECEIVING') RETURNING id"
            ),
            {"mission_id": mission_id, "site_id": site_id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO scan_event_default "
                "(id, event_id, mission_id, event_time, read_type, value) "
                "VALUES (:id, :event_id, :mission_id, "
                "date_trunc('month', CURRENT_DATE) + interval '5 months' + interval '1 day', "
                "'BARCODE', 'partition-proof')"
            ),
            {
                "id": 990000,
                "event_id": uuid.uuid4(),
                "mission_id": mission_pk,
            },
        )

    previous_engine = worker_app.engine
    worker_app.engine = engine
    try:
        result = worker_app.ensure_scan_event_partitions.run(months_ahead=6)
    finally:
        worker_app.engine = previous_engine

    with engine.begin() as connection:
        table_name = connection.execute(
            text(
                "SELECT c.relname FROM scan_event se "
                "JOIN pg_class c ON c.oid = se.tableoid "
                "WHERE se.id = 990000"
            )
        ).scalar_one()
        remaining = connection.execute(
            text("SELECT count(*) FROM scan_event_default")
        ).scalar_one()
        assert table_name.startswith("scan_event_20")
        assert table_name != "scan_event_default"
        assert remaining == 0
        connection.execute(text("DELETE FROM mission WHERE id = :id"), {"id": mission_pk})
        assert result["default_rows_remaining"] == 0
        assert len(result["created_partitions"]) >= 3
    engine.dispose()
