"""Seed script to populate DRIMS database with production/synthetic datasets."""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import engine
from app.models import (
    Base,
    Site,
    Drone,
    Mission,
    Location,
    SKU,
    BinCount,
    BookSnapshot,
    ReconResult,
    DiscrepancyCase,
    AppUser,
    UserRole,
    Setting,
    AuditLog,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo_data")

DATASET_DIR = Path("/app/Dataset/drone_inventory_outputs")
if not DATASET_DIR.is_dir():
    DATASET_DIR = Path(__file__).resolve().parents[1] / "Dataset" / "drone_inventory_outputs"


def load_csv(filename: str):
    path = DATASET_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def map_outcome(raw_outcome: str) -> str:
    raw = (raw_outcome or "").strip().upper()
    mapping = {
        "MATCH": "Match",
        "SHORTAGE": "Shortage",
        "EXCESS": "Excess",
        "MISPLACED": "Misplaced",
        "UNKNOWN_ITEM": "Unknown_item",
        "EMPTY_BIN_MISMATCH": "Empty_bin_mismatch",
        "NOT_SCANNED": "Not_scanned",
    }
    return mapping.get(raw, "Match")


def seed_database():
    logger.info("Starting DRIMS database seeding...")
    
    with Session(engine) as session:
        # 1. Site
        site = session.query(Site).filter(Site.code == "WH01").first()
        if not site:
            logger.info("Creating Site WH01...")
            site = Site(
                name="Main Distribution Facility",
                code="WH01",
                description="Primary automated drone cycle count fulfillment center",
                timezone="UTC",
            )
            session.add(site)
            session.flush()
        site_id = site.id

        # 2. Drone
        drone = session.query(Drone).filter(Drone.serial_number == "DR-01-SN882").first()
        if not drone:
            logger.info("Creating Drone DR-01...")
            drone = Drone(
                serial_number="DR-01-SN882",
                model="Matrice 350 RTK / DIMS Payload",
                firmware_version="v2.4.1",
                site_id=site_id,
                status="IDLE",
            )
            session.add(drone)
            session.flush()
        drone_id = drone.id

        # 3. App Users
        user_specs = [
            ("admin", "admin@drims.local", "Admin"),
            ("controller", "controller@drims.local", "Inventory Controller"),
            ("supervisor", "supervisor@drims.local", "Warehouse Supervisor"),
            ("viewer", "auditor@drims.local", "Viewer"),
            ("system_integration", "integration@drims.local", "System Integration"),
        ]
        for uname, email, role_name in user_specs:
            user = session.query(AppUser).filter(AppUser.username == uname).first()
            if not user:
                user = AppUser(
                    username=uname,
                    email=email,
                    password_hash="managed-by-keycloak",
                    role=role_name,
                    site_id=site_id,
                    is_active=True,
                )
                session.add(user)
                session.flush()
                session.add(UserRole(user_id=user.id, role=role_name))
        session.commit()

        # 4. Settings
        default_settings = [
            ("bin_confidence_weights", {"weights": {"w1": 0.5, "w2": 0.3, "w3": 0.2}}, "Confidence calculation weights (w1: read, w2: location, w3: coverage)"),
            ("discrepancy_variance_threshold", {"variance": 10}, "Variance threshold (qty) to open discrepancy case"),
            ("retention_policies", {"scan_data_days": 730, "hot_images_days": 90, "audit_days": 2555}, "Data lifecycle retention days"),
            ("ira_target", {"target": 98.0}, "Target Item Reconciliation Accuracy percentage"),
        ]
        for key, val, desc in default_settings:
            setting = session.query(Setting).filter(Setting.key == key).first()
            if not setting:
                session.add(Setting(key=key, value=val, description=desc))
        session.commit()

        # 5. SKUs
        sku_count = session.query(SKU).count()
        sku_lookup: Dict[str, int] = {}  # sku_key/gtin -> sku.id
        if sku_count == 0:
            logger.info("Loading SKU Master from CSV...")
            sku_rows = load_csv("sku_master.csv")
            sku_objects = []
            for row in sku_rows:
                unit_val = float(row.get("unit_value") or 1.0) if row.get("unit_value") else 1.0
                desc = (row.get("description") or f"SKU {row.get('sku_id')}")[:490]
                sku_obj = SKU(
                    gtin=row.get("gtin") or None,
                    epc_prefix=row.get("epc_prefix") or None,
                    description=desc,
                    uom=row.get("uom") or "EA",
                    unit_value=unit_val,
                    data_source="production",
                )
                sku_objects.append((row.get("sku_id"), sku_obj))
            
            # Batch add SKUs
            batch_size = 1000
            for i in range(0, len(sku_objects), batch_size):
                batch = sku_objects[i : i + batch_size]
                session.add_all([item[1] for item in batch])
                session.flush()
                for sku_key, obj in batch:
                    if sku_key:
                        sku_lookup[sku_key] = obj.id
            session.commit()
            logger.info("Loaded %d SKUs.", len(sku_objects))
        else:
            logger.info("SKUs already exist (%d records). Building lookup...", sku_count)
            # Reconstruct lookup if needed
            sku_rows = load_csv("sku_master.csv")
            db_skus = {s.gtin: s.id for s in session.query(SKU.gtin, SKU.id).all() if s.gtin}
            for row in sku_rows:
                gtin = row.get("gtin")
                if gtin in db_skus:
                    sku_lookup[row.get("sku_id")] = db_skus[gtin]

        # 6. Locations
        loc_count = session.query(Location).count()
        loc_lookup: Dict[str, int] = {}  # location_id (e.g. LOC00001) -> location.id
        if loc_count == 0:
            logger.info("Loading Warehouse Locations from CSV...")
            loc_rows = load_csv("location.csv")
            loc_objects = []
            for row in loc_rows:
                loc_id = row.get("location_id")
                label_code = row.get("label_code")
                aisle = row.get("aisle", "1")
                rack = row.get("rack", "1")
                level = row.get("level", "1")
                bin_num = row.get("bin", "1")
                zone = row.get("zone", "Z1")

                loc_obj = Location(
                    site_id=site_id,
                    zone_code=zone,
                    aisle_code=f"A{int(aisle):02d}",
                    rack_id=f"R{int(rack):02d}",
                    level_code=f"L{int(level)}",
                    bin_code=loc_id,
                    label_code=label_code,
                    data_source="synthetic",
                )
                loc_objects.append((loc_id, loc_obj))

            batch_size = 1000
            for i in range(0, len(loc_objects), batch_size):
                batch = loc_objects[i : i + batch_size]
                session.add_all([item[1] for item in batch])
                session.flush()
                for lid, obj in batch:
                    loc_lookup[lid] = obj.id
            session.commit()
            logger.info("Loaded %d Locations.", len(loc_objects))
        else:
            logger.info("Locations already exist (%d records). Building lookup...", loc_count)
            for item in session.query(Location.bin_code, Location.id).all():
                loc_lookup[item.bin_code] = item.id

        # 7. Missions
        m1 = session.query(Mission).filter(Mission.mission_id == "MSN-2026-10-09-WH01-001").first()
        if not m1:
            logger.info("Creating Mission MSN-2026-10-09-WH01-001...")
            m1 = Mission(
                mission_id="MSN-2026-10-09-WH01-001",
                drone_id=drone_id,
                site_id=site_id,
                status="RECONCILED",
                coverage_pct=98.4,
                total_scans=19842,
                total_bins_visited=5000,
                started_at=datetime(2026, 10, 9, 5, 30, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 10, 9, 5, 48, 30, tzinfo=timezone.utc),
                data_source="synthetic",
            )
            session.add(m1)
            session.flush()

        m2 = session.query(Mission).filter(Mission.mission_id == "MSN-2026-10-12-WH01-002").first()
        if not m2:
            logger.info("Creating Mission MSN-2026-10-12-WH01-002...")
            m2 = Mission(
                mission_id="MSN-2026-10-12-WH01-002",
                drone_id=drone_id,
                site_id=site_id,
                status="PROCESSING",
                coverage_pct=64.2,
                total_scans=7820,
                total_bins_visited=2100,
                started_at=datetime(2026, 10, 12, 8, 15, 0, tzinfo=timezone.utc),
                data_source="synthetic",
            )
            session.add(m2)
            session.flush()
        session.commit()
        mission_db_id = m1.id

        # 8. Book Snapshots
        bs_count = session.query(BookSnapshot).filter(BookSnapshot.mission_id == mission_db_id).count()
        if bs_count == 0:
            logger.info("Loading Book Snapshots...")
            bs_rows = load_csv("book_snapshot.csv")
            bs_objects = []
            for row in bs_rows:
                loc_id = loc_lookup.get(row.get("location_id"))
                sku_id = sku_lookup.get(row.get("sku_id"))
                if loc_id:
                    bs_objects.append(
                        BookSnapshot(
                            mission_id=mission_db_id,
                            location_id=loc_id,
                            sku_id=sku_id,
                            lot=row.get("lot"),
                            booked_count=int(row.get("book_qty") or 0),
                        )
                    )
            batch_size = 2000
            for i in range(0, len(bs_objects), batch_size):
                session.add_all(bs_objects[i : i + batch_size])
                session.flush()
            session.commit()
            logger.info("Loaded %d Book Snapshots.", len(bs_objects))

        # 9. Bin Counts
        bc_count = session.query(BinCount).filter(BinCount.mission_id == mission_db_id).count()
        if bc_count == 0:
            logger.info("Loading Bin Counts...")
            bc_rows = load_csv("bin_count.csv")
            bc_objects = []
            for row in bc_rows:
                loc_id = loc_lookup.get(row.get("location_id"))
                if loc_id:
                    conf_val = float(row.get("conf") or 0.95)
                    cov_val = float(row.get("coverage") or 0.9)
                    items_qty = int(row.get("items") or 0)
                    bc_objects.append(
                        BinCount(
                            mission_id=mission_db_id,
                            location_id=loc_id,
                            sku_id=None,
                            lot=None,
                            serial=None,
                            count=items_qty,
                            confidence_score=round(conf_val, 4),
                            method="label" if row.get("label_seen") == "True" else "telemetry",
                            image_coverage_ratio=round(cov_val, 4),
                            data_source="synthetic",
                        )
                    )
            batch_size = 2000
            for i in range(0, len(bc_objects), batch_size):
                session.add_all(bc_objects[i : i + batch_size])
                session.flush()
            session.commit()
            logger.info("Loaded %d Bin Counts.", len(bc_objects))

        # 10. Recon Results
        rr_count = session.query(ReconResult).filter(ReconResult.mission_id == mission_db_id).count()
        if rr_count == 0:
            logger.info("Loading Recon Results...")
            rr_rows = load_csv("recon_result.csv")
            rr_objects = []
            for row in rr_rows:
                loc_id = loc_lookup.get(row.get("location_id"))
                sku_id = sku_lookup.get(row.get("sku_key"))
                if loc_id:
                    outcome = map_outcome(row.get("outcome"))
                    var_qty = int(row.get("variance_qty") or 0)
                    rr_objects.append(
                        ReconResult(
                            mission_id=mission_db_id,
                            sku_id=sku_id,
                            location_id=loc_id,
                            lot=row.get("lot"),
                            outcome=outcome,
                            variance=var_qty,
                            confidence=0.95,
                            details={
                                "unit_value": float(row.get("unit_value") or 0.0),
                                "variance_value": float(row.get("variance_value") or 0.0),
                                "counted_qty": int(row.get("counted_qty") or 0),
                                "book_qty": int(row.get("book_qty") or 0),
                            },
                            data_source="synthetic",
                        )
                    )
            batch_size = 2000
            for i in range(0, len(rr_objects), batch_size):
                session.add_all(rr_objects[i : i + batch_size])
                session.flush()
            session.commit()
            logger.info("Loaded %d Recon Results.", len(rr_objects))

        # 11. Discrepancy Cases
        dc_count = session.query(DiscrepancyCase).filter(DiscrepancyCase.mission_id == mission_db_id).count()
        if dc_count == 0:
            logger.info("Loading Discrepancy Cases...")
            dc_rows = load_csv("discrepancy_cases.csv")
            dc_objects = []
            controller_user = session.query(AppUser).filter(AppUser.username == "controller").first()
            ctrl_id = controller_user.id if controller_user else None

            for row in dc_rows:
                loc_id = loc_lookup.get(row.get("location_id"))
                sku_id = sku_lookup.get(row.get("sku_key"))
                if loc_id:
                    outcome = map_outcome(row.get("outcome"))
                    var_val = int(abs(float(row.get("variance_value") or 1.0)))
                    dc_objects.append(
                        DiscrepancyCase(
                            mission_id=mission_db_id,
                            sku_id=sku_id,
                            location_id=loc_id,
                            lot=row.get("lot"),
                            outcome=outcome,
                            variance_value=var_val,
                            threshold_value=10.0,
                            status="open",
                            assigned_to=ctrl_id,
                            data_source="synthetic",
                        )
                    )
            batch_size = 1000
            for i in range(0, len(dc_objects), batch_size):
                session.add_all(dc_objects[i : i + batch_size])
                session.flush()
            session.commit()
            logger.info("Loaded %d Discrepancy Cases.", len(dc_objects))

        # 12. Audit Log
        if session.query(AuditLog).count() == 0:
            logger.info("Adding baseline audit log entries...")
            session.add(
                AuditLog(
                    table_name="mission",
                    record_id=mission_db_id,
                    action="INSERT",
                    old_values=None,
                    new_values={"mission_id": "MSN-2026-10-09-WH01-001", "status": "RECONCILED", "coverage_pct": 98.4},
                    user_id=None,
                )
            )
            session.add(
                AuditLog(
                    table_name="setting",
                    record_id=1,
                    action="INSERT",
                    old_values=None,
                    new_values={"key": "bin_confidence_weights", "weights": {"w1": 0.5, "w2": 0.3, "w3": 0.2}},
                    user_id=None,
                )
            )
            session.commit()

        logger.info("DRIMS database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
