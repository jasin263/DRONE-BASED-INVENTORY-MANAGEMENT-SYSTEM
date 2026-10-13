"""Complete Gate 0 provenance, operational tables, and integrity constraints."""

from alembic import op
import sqlalchemy as sa


revision = "002_gate0_schema"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


DATA_SOURCE = ("abid", "barcode_ref", "synthetic", "production")


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    for table in (
        "location",
        "sku",
        "mission",
        "scan_event",
        "bin_count",
        "recon_result",
        "discrepancy_case",
    ):
        op.add_column(
            table,
            sa.Column(
                "data_source",
                sa.String(20),
                nullable=False,
                server_default="production",
            ),
        )
        op.create_check_constraint(
            f"ck_{table}_data_source",
            table,
            "data_source IN ('abid', 'barcode_ref', 'synthetic', 'production')",
        )
        op.create_index(f"ix_{table}_data_source", table, ["data_source"])

    op.execute(
        """
        ALTER TABLE location
        ALTER COLUMN polygon TYPE geometry(POLYGON, 4326)
        USING CASE
          WHEN polygon IS NULL OR polygon = '' THEN NULL
          ELSE ST_GeomFromText(polygon, 4326)
        END
        """
    )
    op.create_index("ix_location_site_zone", "location", ["site_id", "zone_code"])
    op.create_index("ix_mission_site_created", "mission", ["site_id", "created_at"])
    op.create_index("ix_scan_event_mission_timestamp", "scan_event", ["mission_id", "timestamp"])

    op.create_table(
        "role",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "job",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_status_created", "job", ["status", "created_at"])
    op.create_table(
        "dead_letter",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("queue", sa.String(100), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dead_letter_queue_created", "dead_letter", ["queue", "created_at"])

    # Audit log is append-only at the database boundary.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$;
        DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log;
        CREATE TRIGGER audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")
    op.drop_index("ix_dead_letter_queue_created", table_name="dead_letter")
    op.drop_table("dead_letter")
    op.drop_index("ix_job_status_created", table_name="job")
    op.drop_table("job")
    op.drop_table("role")
    for table in (
        "discrepancy_case",
        "recon_result",
        "bin_count",
        "scan_event",
        "mission",
        "sku",
        "location",
    ):
        op.drop_index(f"ix_{table}_data_source", table_name=table)
        op.drop_constraint(f"ck_{table}_data_source", table_name=table)
        op.drop_column(table, "data_source")
