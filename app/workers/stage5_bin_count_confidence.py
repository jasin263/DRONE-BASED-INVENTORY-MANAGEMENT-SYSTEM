"""Stage 5: Bin count and confidence.

count = distinct items per bin per SKU/lot.
C_bin = w1*avg_read_confidence + w2*location_method_score + w3*image_coverage_ratio,
with w1+w2+w3=1, defaults 0.5/0.3/0.2, location score 1.0 for label and 0.7 for telemetry.
Bins below threshold (default 0.80) are flagged for review.
"""

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from ..models import ScanEvent, ScanItem, BinCount, Setting, scan_event, scan_item, bin_count, setting


def stage5_bin_count_confidence(mission_id: str, db: Session, weights: dict = None):
    """Stage 5: Bin count and confidence.
    
    C_bin = w1*avg_read_confidence + w2*location_method_score + w3*image_coverage_ratio
    Default weights: w1=0.5, w2=0.3, w3=0.2
    Location score: 1.0 for label, 0.7 for telemetry
    """
    
    # Get default weights from settings if not provided
    if weights is None:
        stmt = select(setting.Setting).where(setting.Setting.key == "bin_confidence_weights")
        result = db.execute(stmt)
        setting_row = result.scalar_one_or_none()
        if setting_row and setting_row.value:
            weights = setting_row.value.get("weights", {"w1": 0.5, "w2": 0.3, "w3": 0.2})
        else:
            weights = {"w1": 0.5, "w2": 0.3, "w3": 0.2}
    
    w1 = weights.get("w1", 0.5)
    w2 = weights.get("w2", 0.3)
    w3 = weights.get("w3", 0.2)
    
    # Get all bin counts for this mission
    # Group by location_id, sku_id, lot
    stmt = select(
        scan_item.ScanItem.location_id,
        scan_item.ScanItem.sku_id,
        scan_item.ScanItem.lot,
        func.count(func.distinct(scan_item.ScanItem.serial)).label("distinct_items"),
        func.avg(scan_item.ScanItem.confidence).label("avg_confidence"),
    ).join(
        scan_event.ScanEvent, scan_item.ScanItem.scan_event_id == scan_event.ScanEvent.id
    ).where(
        scan_event.ScanEvent.mission_id == mission_id,
        scan_event.ScanEvent.event_status == "active"
    ).group_by(
        scan_item.ScanItem.location_id,
        scan_item.ScanItem.sku_id,
        scan_item.ScanItem.lot
    )
    result = db.execute(stmt)
    rows = result.all()
    
    created = 0
    
    for row in rows:
        location_id, sku_id, lot, distinct_items, avg_confidence = row
        
        # Determine location method score
        # Check if any scan items at this location use label method
        loc_stmt = select(scan_item.ScanItem.map_method).join(
            scan_event.ScanEvent, scan_item.ScanItem.scan_event_id == scan_event.ScanEvent.id
        ).where(
            scan_event.ScanEvent.mission_id == mission_id,
            scan_event.ScanEvent.event_status == "active",
            scan_item.ScanItem.location_id == location_id
        )
        loc_result = db.execute(loc_stmt)
        methods = [row[0] for row in loc_result.all()]
        
        # Determine location method score
        if "label" in methods:
            loc_score = 1.0
        elif "telemetry" in methods:
            loc_score = 0.7
        else:
            loc_score = 0.5  # default fallback
        
        # Image coverage ratio - placeholder (would need image analysis)
        image_coverage = 0.0  # TODO: analyze images
        
        # Calculate confidence score
        confidence_score = round(w1 * avg_confidence + w2 * loc_score + w3 * image_coverage, 4)
        
        # Check if bin count record already exists
        existing_stmt = select(bin_count.BinCount).where(
            bin_count.BinCount.mission_id == mission_id,
            bin_count.BinCount.location_id == location_id,
            bin_count.BinCount.sku_id == sku_id,
            bin_count.BinCount.lot == lot
        )
        existing_result = db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.count = distinct_items
            existing.confidence_score = confidence_score
            existing.method = "label" if loc_score == 1.0 else "telemetry"
            existing.image_coverage_ratio = image_coverage
        else:
            # Create new
            existing = bin_count.BinCount(
                mission_id=mission_id,
                location_id=location_id,
                sku_id=sku_id,
                lot=lot,
                count=distinct_items,
                confidence_score=confidence_score,
                method="label" if loc_score == 1.0 else "telemetry",
                image_coverage_ratio=image_coverage
            )
            db.add(existing)
        
        created += 1
    
    db.commit()
    
    # Flag bins below threshold
    threshold_stmt = select(setting.Setting).where(setting.Setting.key == "bin_confidence_threshold")
    threshold_result = db.execute(threshold_stmt)
    threshold_row = threshold_result.scalar_one_or_none()
    threshold = threshold_row.value.get("threshold", 0.80) if threshold_row and threshold_row.value else 0.80
    
    # Find flagged bins
    flagged = 0
    for row in rows:
        location_id, sku_id, lot, distinct_items, avg_confidence = row
        # Recalculate to check
        loc_stmt = select(scan_item.ScanItem.map_method).join(
            scan_event.ScanEvent, scan_item.ScanItem.scan_event_id == scan_event.ScanEvent.id
        ).where(
            scan_event.ScanEvent.mission_id == mission_id,
            scan_event.ScanEvent.event_status == "active",
            scan_item.ScanItem.location_id == location_id
        )
        loc_result = db.execute(loc_stmt)
        methods = [row[0] for row in loc_result.all()]
        
        loc_score = 1.0 if "label" in methods else (0.7 if "telemetry" in methods else 0.5)
        confidence_score = round(w1 * avg_confidence + w2 * loc_score + w3 * 0.0, 4)
        
        if confidence_score < threshold:
            # This bin would be flagged - in production would update a flag field
            flagged += 1
    
    return {
        "status": "success",
        "message": f"Stage 5 complete: {created} bin counts computed",
        "created": created,
        "flagged_bins": flagged,
        "weights": weights,
        "threshold": threshold
    }