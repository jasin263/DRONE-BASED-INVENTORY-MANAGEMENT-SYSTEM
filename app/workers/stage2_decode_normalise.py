"""Stage 2: Decode and normalise scan events.

- Parse GS1 AIs (01 GTIN, 10 lot, 17 expiry, 21 serial)
- Map GTIN/EPC to internal SKU via SKU master
- Unknown codes become UNKNOWN_ITEM
"""

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..core.db import engine
from ..models import ScanEvent, ScanItem, SKU


def stage2_decode_normalise(mission_id: str, db: Session):
    """Stage 2: Decode and normalise scan events."""
    
    # Get all scan events for this mission that haven't been decoded yet
    stmt = select(ScanEvent).where(
        ScanEvent.mission_id == mission_id,
        ScanEvent.confidence.isnot(None),
        ScanEvent.id.notin_(
            select(ScanItem.scan_event_id)
        )
    )
    result = db.execute(stmt)
    events = result.scalars().all()
    
    decoded = 0
    
    for event in events:
        value = event.value
        
        # Parse GS1 Application Identifiers
        # Format: (01)GTIN(10)LOT(17)EXPIRY(21)SERIAL
        # Also handle EAN-13, Code-128, QR codes
        
        gtin = None
        lot = None
        expiry = None
        serial = None
        read_type = event.read_type
        
        # Parse GS1 barcode format
        if value.startswith("(01)"):
            # GTIN follows (01)
            gtin_start = 4
            gtin_len = 14  | 8  # EAN-13 or UPC-A
            gtin = value[gtin_start:gtin_start + gtin_len]
            
            # Look for lot (10), expiry (17), serial (21)
            remaining = value[gtin_start + gtin_len:]
            
            # Parse Lot (10)
            if remaining.startswith("(10)"):
                lot_end = remaining.find("(")
                if lot_end == -1:
                    lot_end = len(remaining)
                lot = remaining[4:lot_end]
            
            # Parse Expiry (17)
            if "(17)" in remaining:
                expiry_start = remaining.find("(17)") + 4
                expiry_end = min(
                    remaining.find("(21)") if "(21)" in remaining else len(remaining),
                    remaining.find("(01)") if "(01)" in remaining else len(remaining)
                )
                if expiry_start < expiry_end:
                    expiry = remaining[expiry_start:expiry_end]
            
            # Parse Serial (21)
            if "(21)" in remaining:
                serial_start = remaining.find("(21)") + 4
                serial = remaining[serial_start:]
        
        # Map GTIN to SKU
        sku_id = None
        if gtin:
            stmt = select(SKU).where(SKU.gtin == gtin)
            result = db.execute(stmt)
            found_sku = result.scalar_one_or_none()
            if found_sku:
                sku_id = found_sku.id
        
        # Create scan item
        si = ScanItem(
            scan_event_id=event.id,
            sku_id=sku_id,
            lot=lot,
            serial=serial,
            expiry=__import__("datetime").datetime.strptime(expiry, "%y%m%d").date() if expiry else None,
            map_method="label_fallback",  # Will be updated in stage 3
            is_duplicate=False,
            confidence=event.confidence
        )
        db.add(si)
        decoded += 1
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Stage 2 complete: {decoded} events decoded/normalised",
        "decoded": decoded
    }