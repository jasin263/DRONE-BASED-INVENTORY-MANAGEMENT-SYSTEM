from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, JSON, Enum, Date, Text, ForeignKey, PrimaryKeyConstraint, UniqueConstraint, func

engine = create_engine('postgresql+pg8000://drims:drims_password@localhost:5432/drims', echo=False)

metadata = MetaData()

# Enum types
mission_status = Enum("RECEIVING", "PROCESSING", "RECONCILED", "FAILED", name="missionstatus")
read_type = Enum("BARCODE", "QR", "RFID", name="readtype")
recon_outcome = Enum("Match", "Shortage", "Excess", "Misplaced", "Unknown_item", "Empty_bin_mismatch", "Not_scanned", name="reconoutcome")
user_role = Enum("Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration", name="userrole")
event_status = Enum("active", "archived", "deleted", name="eventstatus")

# === site table ===
site = Table(
    "site", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("name", String(255), nullable=False, unique=True),
    Column("code", String(50), nullable=False, unique=True),
    Column("description", Text(), nullable=True),
    Column("timezone", String(50), nullable=True, default="UTC"),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === drone table ===
drone = Table(
    "drone", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("serial_number", String(100), nullable=False, unique=True),
    Column("model", String(100), nullable=True),
    Column("firmware_version", String(50), nullable=True),
    Column("site_id", Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False),
    Column("status", String(50), nullable=True, default="IDLE"),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === mission table ===
mission = Table(
    "mission", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("mission_id", String(100), nullable=False, unique=True),
    Column("drone_id", Integer, ForeignKey("drone.id", ondelete="SET NULL"), nullable=True),
    Column("site_id", Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False),
    Column("status", mission_status, nullable=False, default="RECEIVING"),
    Column("coverage_pct", Float, nullable=True, default=0.0),
    Column("total_scans", Integer, nullable=True, default=0),
    Column("total_bins_visited", Integer, nullable=True, default=0),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("mission_id", name="uq_mission_external_id"),
)

# === location table ===
location = Table(
    "location", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("site_id", Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False),
    Column("zone_code", String(100), nullable=True),
    Column("aisle_code", String(50), nullable=True),
    Column("rack_id", String(50), nullable=True),
    Column("level_code", String(50), nullable=True),
    Column("bin_code", String(50), nullable=False),
    Column("label_code", String(50), nullable=True),
    Column("polygon", Text(), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("site_id", "bin_code", name="uq_location_site_bin"),
)

# === sku table ===
sku = Table(
    "sku", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("gtin", String(50), nullable=True, unique=True),
    Column("epc_prefix", String(50), nullable=True),
    Column("description", String(500), nullable=True),
    Column("uom", String(50), nullable=True, default="each"),
    Column("unit_value", Float, nullable=True, default=1.0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("gtin", name="uq_sku_gtin"),
)

# === raw_payload table ===
raw_payload = Table(
    "raw_payload", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("mission_id", Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
    Column("received_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("payload_json", JSON(), nullable=False),
    Column("schema_version", String(50), nullable=False),
    Column("stored_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === scan_event table ===
scan_event = Table(
    "scan_event", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("event_id", String(36), nullable=False, unique=True),
    Column("mission_id", Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
    Column("drone_id", Integer, ForeignKey("drone.id", ondelete="SET NULL"), nullable=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("read_type", read_type, nullable=False),
    Column("symbology", String(50), nullable=True),
    Column("value", String(255), nullable=False),
    Column("confidence", Float, nullable=False, default=1.0),
    Column("location_tag", String(100), nullable=True),
    Column("position_x", Float, nullable=True),
    Column("position_y", Float, nullable=True),
    Column("position_z", Float, nullable=True),
    Column("position_frame", String(50), nullable=True),
    Column("image_ref", String(500), nullable=True),
    Column("bbox_x1", Float, nullable=True),
    Column("bbox_y1", Float, nullable=True),
    Column("bbox_x2", Float, nullable=True),
    Column("bbox_y2", Float, nullable=True),
    Column("event_status", event_status, nullable=False, default="active"),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === scan_item table ===
scan_item = Table(
    "scan_item", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("scan_event_id", Integer, ForeignKey("scan_event.id", ondelete="CASCADE"), nullable=False),
    Column("sku_id", Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
    Column("lot", String(100), nullable=True),
    Column("serial", String(100), nullable=True),
    Column("expiry", Date(), nullable=True),
    Column("location_id", Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
    Column("map_method", String(50), nullable=False, default="label_fallback"),
    Column("is_duplicate", Boolean, nullable=False, default=False),
    Column("confidence", Float, nullable=False, default=1.0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === bin_count table ===
bin_count = Table(
    "bin_count", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("mission_id", Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
    Column("location_id", Integer, ForeignKey("location.id", ondelete="CASCADE"), nullable=False),
    Column("sku_id", Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
    Column("lot", String(100), nullable=True),
    Column("serial", String(100), nullable=True),
    Column("count", Integer, nullable=False, default=1),
    Column("confidence_score", Float, nullable=False, default=0.0),
    Column("method", String(50), nullable=False, default="label"),
    Column("image_coverage_ratio", Float, nullable=True, default=0.0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("mission_id", "location_id", "sku_id", "lot", "serial", name="uq_bin_count_unique"),
)

# === book_snapshot table ===
book_snapshot = Table(
    "book_snapshot", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("mission_id", Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
    Column("sku_id", Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
    Column("location_id", Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
    Column("lot", String(100), nullable=True),
    Column("booked_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("mission_id", "sku_id", "location_id", "lot", name="uq_book_snapshot_unique"),
)

# === recon_result table ===
recon_result = Table(
    "recon_result", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("mission_id", Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
    Column("sku_id", Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
    Column("location_id", Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
    Column("lot", String(100), nullable=True),
    Column("outcome", recon_outcome, nullable=False),
    Column("variance", Integer, nullable=True),
    Column("confidence", Float, nullable=True),
    Column("details", JSON(), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === discrepancy_case table ===
discrepancy_case = Table(
    "discrepancy_case", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("mission_id", Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False),
    Column("sku_id", Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
    Column("location_id", Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
    Column("lot", String(100), nullable=True),
    Column("outcome", recon_outcome, nullable=False),
    Column("variance_value", Integer, nullable=True),
    Column("threshold_value", Float, nullable=True),
    Column("status", String(50), nullable=False, default="open"),
    Column("assigned_to", Integer, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === case_comment table ===
case_comment = Table(
    "case_comment", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("case_id", Integer, ForeignKey("discrepancy_case.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=False),
    Column("comment", Text(), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === adjustment table ===
adjustment = Table(
    "adjustment", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("case_id", Integer, ForeignKey("discrepancy_case.id", ondelete="SET NULL"), nullable=True),
    Column("sku_id", Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True),
    Column("location_id", Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True),
    Column("adjustment_type", String(50), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("reason", String(255), nullable=True),
    Column("status", String(50), nullable=False, default="pending"),
    Column("posted_to_erp", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === app_user table ===
app_user = Table(
    "app_user", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("username", String(255), nullable=False, unique=True),
    Column("email", String(255), nullable=True, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", user_role, nullable=False, default="Viewer"),
    Column("site_id", Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=True),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === user_role table ===
user_role_table = Table(
    "user_role", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("user_id", Integer, ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False),
    Column("role", user_role, nullable=False),
    Column("granted_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("user_id", "role", name="uq_user_role_unique"),
)

# === setting table ===
setting = Table(
    "setting", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("key", String(100), nullable=False, unique=True),
    Column("value", JSON(), nullable=False),
    Column("description", String(255), nullable=True),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# === audit_log table ===
audit_log = Table(
    "audit_log", metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("table_name", String(100), nullable=False),
    Column("record_id", Integer, nullable=False),
    Column("action", String(50), nullable=False),
    Column("old_values", JSON(), nullable=True),
    Column("new_values", JSON(), nullable=True),
    Column("user_id", Integer, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# Create all tables
metadata.create_all(engine)
print("All tables created successfully!")

# Verify
with engine.connect() as conn:
    result = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = result.fetchall()
    print(f"Tables created: {[t[0] for t in tables]}")