"""SQLAlchemy ORM models for DIMS application.

Maps to the PostgreSQL database tables defined in Phase 1 foundation.
Uses SQLAlchemy 1.4 compatible syntax.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, JSON, Date,
    Enum as SQLAEnum, ForeignKey, ForeignKeyConstraint, UniqueConstraint, event
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from types import SimpleNamespace

from .core.config import settings
from .core.db import engine

# Enum definitions (must match PostgreSQL ENUM types or use string values)
mission_status_enum = ["RECEIVING", "PROCESSING", "RECONCILED", "FAILED"]
read_type_enum = ["BARCODE", "QR", "RFID", "LOCATION"]
recon_outcome_enum = [
    "Match", "Shortage", "Excess", "Misplaced",
    "Unknown_item", "Empty_bin_mismatch", "Not_scanned"
]
user_role_enum = ["Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"]
event_status_enum = ["active", "archived", "deleted"]

# Base class
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ============================================
# Enum helpers for SQLAlchemy 1.4
# ============================================

def make_enum(enum_values, name=None):
    """Create a SQLAlchemy Enum from a list of strings."""
    from sqlalchemy import String as SA_String
    return SQLAEnum(
        *enum_values,
        name=name,
        native_enum=False,  # Use string values instead of PostgreSQL ENUM type
    )


# ============================================
# Site table
# ============================================

class Site(Base):
    """Multi-site support table."""
    __tablename__ = "site"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    timezone = Column(String(50), nullable=True, default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    drones = relationship("Drone", back_populates="site")
    missions = relationship("Mission", back_populates="site")
    locations = relationship("Location", back_populates="site")
    users = relationship("AppUser", back_populates="site")


# ============================================
# Drone table
# ============================================

class Drone(Base):
    """Drone information table."""
    __tablename__ = "drone"

    id = Column(Integer, primary_key=True, nullable=False)
    serial_number = Column(String(100), nullable=False, unique=True)
    model = Column(String(100), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=True, default="IDLE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    site = relationship("Site", back_populates="drones")
    missions = relationship("Mission", back_populates="drone")
    scan_events = relationship("ScanEvent", back_populates="drone")


# ============================================
# Mission table
# ============================================

class Mission(Base):
    """Mission/flight record table."""
    __tablename__ = "mission"

    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(String(100), nullable=False, unique=True)  # external UUID
    drone_id = Column(Integer, ForeignKey("drone.id", ondelete="SET NULL"), nullable=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLAEnum(*mission_status_enum, name="missionstatus", native_enum=False), nullable=False, default="RECEIVING")
    coverage_pct = Column(Float, nullable=True, default=0.0)
    total_scans = Column(Integer, nullable=True, default=0)
    total_bins_visited = Column(Integer, nullable=True, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    site = relationship("Site", back_populates="missions")
    drone = relationship("Drone", back_populates="missions")
    raw_payloads = relationship("RawPayload", back_populates="mission")
    scan_events = relationship("ScanEvent", back_populates="mission")
    bin_counts = relationship("BinCount", back_populates="mission")
    book_snapshot = relationship("BookSnapshot", back_populates="mission", uselist=False)
    recon_results = relationship("ReconResult", back_populates="mission")
    discrepancy_cases = relationship("DiscrepancyCase", back_populates="mission")


# ============================================
# Location table
# ============================================

class Location(Base):
    """Rack/location table with PostGIS polygon support."""
    __tablename__ = "location"

    id = Column(Integer, primary_key=True, nullable=False)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    zone_code = Column(String(100), nullable=True)
    aisle_code = Column(String(50), nullable=True)
    rack_id = Column(String(50), nullable=True)
    level_code = Column(String(50), nullable=True)
    bin_code = Column(String(50), nullable=False)
    label_code = Column(String(50), nullable=True)
    polygon = Column(Text, nullable=True)  # PostWKT or GeoJSON for PostGIS polygon
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("site_id", "bin_code", name="uq_location_site_bin"),
    )

    # Relationships
    site = relationship("Site", back_populates="locations")
    scan_items = relationship("ScanItem", back_populates="location")
    bin_counts = relationship("BinCount", back_populates="location")
    book_snapshot = relationship("BookSnapshot", back_populates="location", uselist=False)
    discrepancy_cases = relationship("DiscrepancyCase", back_populates="location")
    recon_results = relationship("ReconResult", back_populates="location")
    adjustments = relationship("Adjustment", back_populates="location")


# ============================================
# SKU table
# ============================================

class SKU(Base):
    """Stock Keeping Unit master table."""
    __tablename__ = "sku"

    id = Column(Integer, primary_key=True, nullable=False)
    gtin = Column(String(50), nullable=True, unique=True)
    epc_prefix = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
    uom = Column(String(50), nullable=True, default="each")
    unit_value = Column(Float, nullable=True, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("gtin", name="uq_sku_gtin"),
    )

    # Relationships
    scan_items = relationship("ScanItem", back_populates="sku")
    bin_counts = relationship("BinCount", back_populates="sku")
    book_snapshot = relationship("BookSnapshot", back_populates="sku", uselist=False)
    recon_results = relationship("ReconResult", back_populates="sku")
    discrepancy_cases = relationship("DiscrepancyCase", back_populates="sku")
    adjustments = relationship("Adjustment", back_populates="sku")


# ============================================
# RawPayload table
# ============================================

class RawPayload(Base):
    """Bronze layer: stored raw ingest payloads."""
    __tablename__ = "raw_payload"

    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload_json = Column(JSON, nullable=False)  # raw event payload
    schema_version = Column(String(50), nullable=False)
    stored_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mission = relationship("Mission", back_populates="raw_payloads")


# ============================================
# ScanEvent table
# ============================================

class ScanEvent(Base):
    """Silver layer: individual scan events partitioned by event month."""
    __tablename__ = "scan_event"

    id = Column(Integer, primary_key=True, nullable=False)
    event_id = Column(String(36), nullable=False, unique=True)  # UUID as string
    mission_id = Column(Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False)
    drone_id = Column(Integer, ForeignKey("drone.id", ondelete="SET NULL"), nullable=True)
    event_time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    read_type = Column(SQLAEnum(*read_type_enum, name="readtype", native_enum=False), nullable=False)
    symbology = Column(String(50), nullable=True)  # EAN-13, Code-128, QR, RFID EPC etc
    value = Column(String(255), nullable=False)  # raw scanned value
    confidence = Column(Float, nullable=False, default=1.0)
    location_tag = Column(String(100), nullable=True)  # e.g. "WH01-A12-R03-L2-B04"
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)
    position_frame = Column(String(50), nullable=True)
    image_ref = Column(String(500), nullable=True)  # MinIO object key
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)
    event_status = Column(SQLAEnum(*event_status_enum, name="eventstatus", native_enum=False), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mission = relationship("Mission", back_populates="scan_events")
    drone = relationship("Drone", back_populates="scan_events")
    scan_item = relationship("ScanItem", back_populates="scan_event", uselist=False)


# ============================================
# ScanItem table
# ============================================

class ScanItem(Base):
    """Denormalized item per scan event - after decoding/normalisation."""
    __tablename__ = "scan_item"

    id = Column(Integer, primary_key=True, nullable=False)
    scan_event_id = Column(Integer, nullable=False)
    scan_event_time = Column(DateTime(timezone=True), nullable=False)
    sku_id = Column(Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True)
    lot = Column(String(100), nullable=True)
    serial = Column(String(100), nullable=True)
    expiry = Column(Date, nullable=True)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True)
    map_method = Column(String(50), nullable=False, default="label_fallback")  # "label" or "telemetry"
    is_duplicate = Column(Boolean, nullable=False, default=False)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["scan_event_id", "scan_event_time"],
            ["scan_event.id", "scan_event.event_time"],
            ondelete="CASCADE",
        ),
    )

    # Relationships
    scan_event = relationship("ScanEvent", back_populates="scan_item")
    sku = relationship("SKU", back_populates="scan_items")
    location = relationship("Location", back_populates="scan_items")


# ============================================
# BinCount table
# ============================================

class BinCount(Base):
    """Computed bin counts per mission."""
    __tablename__ = "bin_count"

    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True)
    lot = Column(String(100), nullable=True)
    serial = Column(String(100), nullable=True)
    count = Column(Integer, nullable=False, default=1)
    confidence_score = Column(Float, nullable=False, default=0.0)
    method = Column(String(50), nullable=False, default="label")  # "label" or "telemetry"
    image_coverage_ratio = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("mission_id", "location_id", "sku_id", "lot", "serial", name="uq_bin_count_unique"),
    )

    # Relationships
    mission = relationship("Mission", back_populates="bin_counts")
    location = relationship("Location", back_populates="bin_counts")
    sku = relationship("SKU", back_populates="bin_counts")


# ============================================
# BookSnapshot table
# ============================================

class BookSnapshot(Base):
    """Book stock snapshot taken at mission start."""
    __tablename__ = "book_snapshot"

    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True)
    lot = Column(String(100), nullable=True)
    booked_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("mission_id", "sku_id", "location_id", "lot", name="uq_book_snapshot_unique"),
    )

    # Relationships
    mission = relationship("Mission", back_populates="book_snapshot")
    sku = relationship("SKU", back_populates="book_snapshot")
    location = relationship("Location", back_populates="book_snapshot")


# ============================================
# ReconResult table
# ============================================

class ReconResult(Base):
    """Reconciliation results per mission/SKU/bin."""
    __tablename__ = "recon_result"

    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True)
    lot = Column(String(100), nullable=True)
    outcome = Column(SQLAEnum(*recon_outcome_enum, name="reconoutcome", native_enum=False), nullable=False)
    variance = Column(Integer, nullable=True)  # difference between counted and booked
    confidence = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)  # additional rationale
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mission = relationship("Mission", back_populates="recon_results")
    sku = relationship("SKU", back_populates="recon_results")
    location = relationship("Location", back_populates="recon_results")


# ============================================
# DiscrepancyCase table
# ============================================

class DiscrepancyCase(Base):
    """Open discrepancy cases (shortage/excess if variance exceeds threshold)."""
    __tablename__ = "discrepancy_case"

    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(Integer, ForeignKey("mission.id", ondelete="CASCADE"), nullable=False)
    sku_id = Column(Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True)
    lot = Column(String(100), nullable=True)
    outcome = Column(SQLAEnum(*recon_outcome_enum, name="reconoutcome", native_enum=False), nullable=False)
    variance_value = Column(Integer, nullable=True)  # absolute variance
    threshold_value = Column(Float, nullable=True)  # configurable threshold
    status = Column(String(50), nullable=False, default="open")  # "open", "approved", "rejected"
    assigned_to = Column(Integer, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mission = relationship("Mission", back_populates="discrepancy_cases")
    sku = relationship("SKU", back_populates="discrepancy_cases")
    location = relationship("Location", back_populates="discrepancy_cases")
    assigned_user = relationship("AppUser", back_populates="assigned_cases", foreign_keys=[assigned_to])
    case_comments = relationship("CaseComment", back_populates="case")
    adjustments = relationship("Adjustment", back_populates="case")


# ============================================
# CaseComment table
# ============================================

class CaseComment(Base):
    """Comments on discrepancy cases."""
    __tablename__ = "case_comment"

    id = Column(Integer, primary_key=True, nullable=False)
    case_id = Column(Integer, ForeignKey("discrepancy_case.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    case = relationship("DiscrepancyCase", back_populates="case_comments")
    user = relationship("AppUser", back_populates="comments_made")


# ============================================
# Adjustment table
# ============================================

class Adjustment(Base):
    """Stock adjustments from discrepancy resolution."""
    __tablename__ = "adjustment"

    id = Column(Integer, primary_key=True, nullable=False)
    case_id = Column(Integer, ForeignKey("discrepancy_case.id", ondelete="SET NULL"), nullable=True)
    sku_id = Column(Integer, ForeignKey("sku.id", ondelete="SET NULL"), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id", ondelete="SET NULL"), nullable=True)
    adjustment_type = Column(String(50), nullable=False)  # "add", "remove", "transfer"
    quantity = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # "pending", "posted", "failed"
    posted_to_erp = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    case = relationship("DiscrepancyCase", back_populates="adjustments")
    sku = relationship("SKU", back_populates="adjustments")
    location = relationship("Location", back_populates="adjustments")


# ============================================
# AppUser table
# ============================================

class AppUser(Base):
    """Application users with RBAC."""
    __tablename__ = "app_user"

    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLAEnum(*user_role_enum, name="userrole", native_enum=False), nullable=False, default="Viewer")
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    site = relationship("Site", back_populates="users")
    assigned_cases = relationship("DiscrepancyCase", back_populates="assigned_user")
    comments_made = relationship("CaseComment", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user")
    audit_entries = relationship("AuditLog", back_populates="user")


# ============================================
# UserRole table
# ============================================

class UserRole(Base):
    """User-role assignment for RBAC."""
    __tablename__ = "user_role"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLAEnum(*user_role_enum, name="userrole", native_enum=False), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_user_role_unique"),
    )

    # Relationships
    user = relationship("AppUser", back_populates="user_roles")


# ============================================
# Setting table
# ============================================

class Setting(Base):
    """Configurable thresholds and weights."""
    __tablename__ = "setting"

    id = Column(Integer, primary_key=True, nullable=False)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(JSON, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ============================================
# AuditLog table
# ============================================

class AuditLog(Base):
    """Append-only audit log for all changes."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, nullable=False)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # "INSERT", "UPDATE", "DELETE"
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("AppUser", back_populates="audit_entries")


# Compatibility namespaces for the original worker modules.  New code should
# import the ORM classes directly.
mission = SimpleNamespace(Mission=Mission)
raw_payload = SimpleNamespace(RawPayload=RawPayload)
scan_event = SimpleNamespace(ScanEvent=ScanEvent)
scan_item = SimpleNamespace(ScanItem=ScanItem)
site = SimpleNamespace(Site=Site)
drone = SimpleNamespace(Drone=Drone)
sku = SimpleNamespace(SKU=SKU)
location = SimpleNamespace(Location=Location)
bin_count = SimpleNamespace(BinCount=BinCount)
book_snapshot = SimpleNamespace(BookSnapshot=BookSnapshot)
recon_result = SimpleNamespace(ReconResult=ReconResult)
discrepancy_case = SimpleNamespace(DiscrepancyCase=DiscrepancyCase)
case_comment = SimpleNamespace(CaseComment=CaseComment)
adjustment = SimpleNamespace(Adjustment=Adjustment)
app_user = SimpleNamespace(AppUser=AppUser)
user_role = SimpleNamespace(UserRole=UserRole)
setting = SimpleNamespace(Setting=Setting)
outcome_enum = recon_outcome_enum