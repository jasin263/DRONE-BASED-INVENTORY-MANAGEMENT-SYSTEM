"""Initial migration: core tables for Phase 1 foundation.

Creates: site, drone, mission, location, sku tables.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types
    site_status_enum = sa.Enum("RECEIVING", "PROCESSING", "RECONCILED", "FAILED", name="missionstatus", create_type=True)
    read_type_enum = sa.Enum("BARCODE", "QR", "RFID", name="readtype", create_type=True)
    outcome_enum = sa.Enum("Match", "Shortage", "Excess", "Misplaced", "Unknown_item", "Empty_bin_mismatch", "Not_scanned", name="reconoutcome", create_type=True)
    role_enum = sa.Enum("Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration", name="userrole", create_type=True)
    event_status_enum = sa.Enum("active", "archived", "deleted", name="eventstatus", create_type=True)

    # CREATE EXTENSION postgis (already assumed installed)

    # === site table ===
    op.create_table(
        "site",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True, default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === drone table ===
    op.create_table(
        "drone",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=False, unique=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("site.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=True, default="IDLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === mission table ===
    site_id_col = sa.Column("site_id", sa.Integer, sa.ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    mission_status_enum = sa.Enum("RECEIVING", "PROCESSING", "RECONCILED", "FAILED", name="missionstatus", create_type=True)

    op.create_table(
        "mission",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("mission_id", sa.String(100), nullable=False, unique=True),  # external mission UUID
        sa.Column("drone_id", sa.Integer, sa.ForeignKey("drone.id", ondelete="SET NULL"), nullable=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("site.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", mission_status_enum, nullable=False, default="RECEIVING"),
        sa.Column("coverage_pct", sa.Float, nullable=True, default=0.0),
        sa.Column("total_scans", sa.Integer, nullable=True, default=0),
        sa.Column("total_bins_visited", sa.Integer, nullable=True, default=0),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mission_id", name="uq_mission_external_id"),
    )

    # === location table (zone, aisle, rack, level, bin) ===
    op.create_table(
        "location",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("site.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_code", sa.String(100), nullable=True),
        sa.Column("aisle_code", sa.String(50), nullable=True),
        sa.Column("rack_id", sa.String(50), nullable=True),
        sa.Column("level_code", sa.String(50), nullable=True),
        sa.Column("bin_code", sa.String(50), nullable=False),
        sa.Column("label_code", sa.String(50), nullable=True),
        sa.Column("polygon", sa.Text(), nullable=True),  # PostWKT or GeoJSON for PostGIS polygon
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("site_id", "bin_code", name="uq_location_site_bin"),
    )

    # === sku table ===
    op.create_table(
        "sku",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("gtin", sa.String(50), nullable=True, unique=True),
        sa.Column("epc_prefix", sa.String(50), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("uom", sa.String(50), nullable=True, default="each"),
        sa.Column("unit_value", sa.Float, nullable=True, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("gtin", name="uq_sku_gtin"),
    )

    # === raw_payload table: stores incoming scan events (bronze layer) ===
    op.create_table(
        "raw_payload",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),  # raw event payload
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === scan_event table: partitioned scan events (silver layer) ===
    op.create_table(
        "scan_event",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False, unique=True),  # UUID idempotency key
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drone_id", sa.Integer, sa.ForeignKey("drone.id", ondelete="SET NULL"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_type", read_type_enum, nullable=False),
        sa.Column("symbology", sa.String(50), nullable=True),  # EAN-13, Code-128, QR, RFID EPC etc
        sa.Column("value", sa.String(255), nullable=False, comment="raw scanned value (e.g. GS1 barcode)"),
        sa.Column("confidence", sa.Float, nullable=False, default=1.0),
        sa.Column("location_tag", sa.String(100), nullable=True),  # e.g. "WH01-A12-R03-L2-B04"
        sa.Column("position_x", sa.Float, nullable=True),
        sa.Column("position_y", sa.Float, nullable=True),
        sa.Column("position_z", sa.Float, nullable=True),
        sa.Column("position_frame", sa.String(50), nullable=True),
        sa.Column("image_ref", sa.String(500), nullable=True),  # MinIO object key
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("bbox_x2", sa.Float, nullable=True),
        sa.Column("bbox_y2", sa.Float, nullable=True),
        sa.Column("event_status", event_status_enum, nullable=False, default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Note: scan_event partitioned by month would be handled via pg_partman or application logic

    # === scan_item table: denormalized item per scan event ===
    op.create_table(
        "scan_item",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("scan_event_id", sa.Integer, sa.ForeignKey("scan_event.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.Integer, sa.ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot", sa.String(100), nullable=True),
        sa.Column("serial", sa.String(100), nullable=True),
        sa.Column("expiry", sa.Date, nullable=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
        sa.Column("map_method", sa.String(50), nullable=False, default="label_fallback"),  # "label" or "telemetry"
        sa.Column("is_duplicate", sa.Boolean, nullable=False, default=False),
        sa.Column("confidence", sa.Float, nullable=False, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === bin_count table: computed bin counts per mission ===
    op.create_table(
        "bin_count",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.Integer, sa.ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot", sa.String(100), nullable=True),
        sa.Column("serial", sa.String(100), nullable=True),
        sa.Column("count", sa.Integer, nullable=False, default=1),
        sa.Column("confidence_score", sa.Float, nullable=False, default=0.0),
        sa.Column("method", sa.String(50), nullable=False, default="label"),  # "label" or "telemetry"
        sa.Column("image_coverage_ratio", sa.Float, nullable=True, default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mission_id", "location_id", "sku_id", "lot", "serial", name="uq_bin_count_unique"),
    )

    # === book_snapshot: book stock at mission start ===
    op.create_table(
        "book_snapshot",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.Integer, sa.ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot", sa.String(100), nullable=True),
        sa.Column("booked_count", sa.Integer, nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mission_id", "sku_id", "location_id", "lot", name="uq_book_snapshot_unique"),
    )

    # === recon_result table: reconciliation results ===
    op.create_table(
        "recon_result",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.Integer, sa.ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot", sa.String(100), nullable=True),
        sa.Column("outcome", outcome_enum, nullable=False),
        sa.Column("variance", sa.Integer, nullable=True),  # difference between counted and booked
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),  # additional rationale
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create users before discrepancy tables because cases/comments reference them.
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", role_enum, nullable=False, default="Viewer"),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("site.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === discrepancy_case table: open discrepancy cases ===
    op.create_table(
        "discrepancy_case",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.Integer, sa.ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lot", sa.String(100), nullable=True),
        sa.Column("outcome", outcome_enum, nullable=False),
        sa.Column("variance_value", sa.Integer, nullable=True),  # absolute variance
        sa.Column("threshold_value", sa.Float, nullable=True),  # configurable threshold
        sa.Column("status", sa.String(50), nullable=False, default="open"),  # "open", "approved", "rejected"
        sa.Column("assigned_to", sa.Integer, sa.ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === case_comment table: comments on discrepancy cases ===
    op.create_table(
        "case_comment",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("discrepancy_case.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("app_user.id", ondelete="SET NULL"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === adjustment table: stock adjustments ===
    op.create_table(
        "adjustment",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("discrepancy_case.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sku_id", sa.Integer, sa.ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
        sa.Column("adjustment_type", sa.String(50), nullable=False),  # "add", "remove", "transfer"
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),  # "pending", "posted", "failed"
        sa.Column("posted_to_erp", sa.Boolean, nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === role and user_role tables for RBAC ===
    op.create_table(
        "user_role",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role_unique"),
    )

    # === setting table: configurable thresholds and weights ===
    op.create_table(
        "setting",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === audit_log table: append-only JSONB audit log ===
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("action", sa.String(50), nullable=False),  # "INSERT", "UPDATE", "DELETE"
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order (dependencies respected)
    op.drop_table("audit_log")
    op.drop_table("setting")
    op.drop_table("user_role")
    op.drop_table("app_user")
    op.drop_table("discrepancy_case")
    op.drop_table("case_comment")
    op.drop_table("recon_result")
    op.drop_table("book_snapshot")
    op.drop_table("bin_count")
    op.drop_table("scan_item")
    op.drop_table("scan_event")
    op.drop_table("raw_payload")
    op.drop_table("sku")
    op.drop_table("location")
    op.drop_table("mission")
    op.drop_table("drone")
    op.drop_table("site")

    # Drop enums
    for enum_name in ["userrole", "missionstatus", "readtype", "reconoutcome", "eventstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")